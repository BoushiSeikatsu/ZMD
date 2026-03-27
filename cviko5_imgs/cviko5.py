import argparse
import sys

import cv2
import numpy as np


VALID_METRICS = {"SAD", "NCC", "CENSUS", "RANK"}
NCC_EPS = 1e-8

# Fast byte popcount lookup used by Census Hamming distance.
POPCOUNT_LUT = np.unpackbits(np.arange(256, dtype=np.uint8)[:, None], axis=1).sum(axis=1).astype(np.uint8)


def parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(
		prog="./stereo",
		description="Compute left-view disparity map from a rectified stereo pair.",
	)
	parser.add_argument("img_l", help="Path to left grayscale image")
	parser.add_argument("img_r", help="Path to right grayscale image")
	parser.add_argument("max_disp", type=int, help="Maximum disparity (inclusive)")
	parser.add_argument("metric", help="Matching metric: SAD, NCC, Census, Rank")
	parser.add_argument("window_size", type=int, help="Odd matching window size >= 3")
	parser.add_argument("img_output", help="Output path for disparity visualization")
	return parser.parse_args()


def box_sum(image: np.ndarray, window_size: int) -> np.ndarray:
	return cv2.boxFilter(
		image,
		ddepth=-1,
		ksize=(window_size, window_size),
		normalize=False,
		borderType=cv2.BORDER_CONSTANT,
	)


def shift_image(image: np.ndarray, dy: int, dx: int, fill_value: int = 0) -> np.ndarray:
	h, w = image.shape
	shifted = np.full((h, w), fill_value, dtype=image.dtype)

	if dy >= 0:
		src_y0, src_y1 = 0, h - dy
		dst_y0, dst_y1 = dy, h
	else:
		src_y0, src_y1 = -dy, h
		dst_y0, dst_y1 = 0, h + dy

	if dx >= 0:
		src_x0, src_x1 = 0, w - dx
		dst_x0, dst_x1 = dx, w
	else:
		src_x0, src_x1 = -dx, w
		dst_x0, dst_x1 = 0, w + dx

	if src_y1 > src_y0 and src_x1 > src_x0:
		shifted[dst_y0:dst_y1, dst_x0:dst_x1] = image[src_y0:src_y1, src_x0:src_x1]
	return shifted


def census_transform(image: np.ndarray, window_size: int) -> np.ndarray:
	h, w = image.shape
	radius = window_size // 2
	num_bits = window_size * window_size - 1
	num_bytes = (num_bits + 7) // 8
	census = np.zeros((h, w, num_bytes), dtype=np.uint8)

	bit_index = 0
	for dy in range(-radius, radius + 1):
		for dx in range(-radius, radius + 1):
			if dy == 0 and dx == 0:
				continue
			neighbor = shift_image(image, dy, dx, fill_value=0)
			bits = (neighbor >= image).astype(np.uint8)
			byte_index = bit_index // 8
			bit_offset = bit_index % 8
			census[:, :, byte_index] |= bits << bit_offset
			bit_index += 1

	return census


def rank_transform(image: np.ndarray, window_size: int) -> np.ndarray:
	radius = window_size // 2
	rank = np.zeros(image.shape, dtype=np.uint16)

	for dy in range(-radius, radius + 1):
		for dx in range(-radius, radius + 1):
			if dy == 0 and dx == 0:
				continue
			neighbor = shift_image(image, dy, dx, fill_value=0)
			rank += (neighbor < image).astype(np.uint16)

	return rank


def compute_valid_mask(height: int, width: int, max_disp: int, window_size: int) -> np.ndarray:
	radius = window_size // 2
	valid = np.ones((height, width), dtype=bool)

	if radius > 0:
		valid[:radius, :] = False
		valid[height - radius :, :] = False
		valid[:, width - radius :] = False

	left_invalid = min(width, max_disp + radius)
	if left_invalid > 0:
		valid[:, :left_invalid] = False

	return valid


def load_grayscale(path: str) -> np.ndarray:
	image = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
	if image is None:
		raise FileNotFoundError(f"Could not load image: {path}")
	return image


def validate_inputs(left: np.ndarray, right: np.ndarray, max_disp: int, metric: str, window_size: int) -> None:
	if left.shape != right.shape:
		raise ValueError("Left and right images must have the same shape.")
	if max_disp < 0:
		raise ValueError("max_disp must be >= 0.")
	if max_disp >= left.shape[1]:
		raise ValueError("max_disp must be smaller than image width.")
	if window_size < 3 or window_size % 2 == 0:
		raise ValueError("window_size must be odd and >= 3.")
	h, w = left.shape
	radius = window_size // 2
	if window_size > min(h, w):
		raise ValueError(
			f"Invalid geometry: window_size ({window_size}) must be <= min(image height, image width) ({min(h, w)})."
		)
	if 2 * radius >= h:
		raise ValueError(
			f"Invalid geometry: 2*radius ({2 * radius}) must be < image height ({h}) to keep a non-empty vertical valid region."
		)
	if max_disp + radius >= w:
		raise ValueError(
			f"Invalid geometry: max_disp + radius ({max_disp + radius}) must be < image width ({w}) to keep a non-empty horizontal valid region."
		)
	valid_h = h - 2 * radius
	valid_w = w - (max_disp + radius)
	if valid_h <= 0 or valid_w <= 0:
		raise ValueError(
			f"Invalid geometry: valid region must be positive, got height={valid_h}, width={valid_w}."
		)
	if metric not in VALID_METRICS:
		raise ValueError("metric must be one of: SAD, NCC, Census, Rank.")


def compute_disparity(
	left: np.ndarray,
	right: np.ndarray,
	max_disp: int,
	metric: str,
	window_size: int,
) -> np.ndarray:
	h, w = left.shape
	left_f = left.astype(np.float32)
	right_f = right.astype(np.float32)
	n = float(window_size * window_size)

	census_left = census_right = None
	rank_left = rank_right = None

	if metric == "CENSUS":
		census_left = census_transform(left, window_size)
		census_right = census_transform(right, window_size)
	elif metric == "RANK":
		rank_left = rank_transform(left, window_size)
		rank_right = rank_transform(right, window_size)

	best_cost = np.full((h, w), np.inf, dtype=np.float32)
	best_disp = np.zeros((h, w), dtype=np.uint16)

	for d in range(max_disp + 1):
		overlap = w - d
		if overlap <= 0:
			break

		if metric == "SAD":
			diff = np.abs(left_f[:, d:] - right_f[:, :overlap])
			cost_slice = box_sum(diff, window_size)
		elif metric == "NCC":
			l_slice = left_f[:, d:]
			r_slice = right_f[:, :overlap]

			sum_l = box_sum(l_slice, window_size)
			sum_r = box_sum(r_slice, window_size)
			sum_l2 = box_sum(l_slice * l_slice, window_size)
			sum_r2 = box_sum(r_slice * r_slice, window_size)
			sum_lr = box_sum(l_slice * r_slice, window_size)

			cov = sum_lr - (sum_l * sum_r) / n
			var_l = np.maximum(sum_l2 - (sum_l * sum_l) / n, 0.0)
			var_r = np.maximum(sum_r2 - (sum_r * sum_r) / n, 0.0)
			denom = np.sqrt(var_l * var_r) + NCC_EPS
			ncc = cov / denom
			cost_slice = 1.0 - np.clip(ncc, -1.0, 1.0)
		elif metric == "CENSUS":
			xor = np.bitwise_xor(census_left[:, d:, :], census_right[:, :overlap, :])
			cost_slice = POPCOUNT_LUT[xor].sum(axis=2, dtype=np.uint16).astype(np.float32)
		else:  # metric == "RANK"
			rank_diff = rank_left[:, d:].astype(np.int32) - rank_right[:, :overlap].astype(np.int32)
			cost_slice = box_sum(np.abs(rank_diff).astype(np.float32), window_size)

		best_cost_slice = best_cost[:, d:]
		best_disp_slice = best_disp[:, d:]
		better = cost_slice < best_cost_slice
		best_cost_slice[better] = cost_slice[better]
		best_disp_slice[better] = d

	return best_disp


def main() -> int:
	args = parse_args()
	metric = args.metric.strip().upper()

	left = load_grayscale(args.img_l)
	right = load_grayscale(args.img_r)
	validate_inputs(left, right, args.max_disp, metric, args.window_size)

	disparity = compute_disparity(left, right, args.max_disp, metric, args.window_size)
	valid_mask = compute_valid_mask(left.shape[0], left.shape[1], args.max_disp, args.window_size)

	# Scale disparity to 8-bit using configured max disparity; keep zero-safe behavior.
	scale = 255.0 / float(args.max_disp) if args.max_disp > 0 else 0.0
	disparity_vis = np.clip(disparity.astype(np.float32) * scale, 0.0, 255.0).astype(np.uint8)
	disparity_vis[~valid_mask] = 0

	if not cv2.imwrite(args.img_output, disparity_vis):
		raise RuntimeError(f"Could not write output image: {args.img_output}")

	return 0


if __name__ == "__main__":
	try:
		raise SystemExit(main())
	except Exception as exc:
		print(f"Error: {exc}", file=sys.stderr)
		raise SystemExit(1)
