from pathlib import Path

import cv2 as cv
import numpy as np


def find_first_working_pattern(image_paths, pattern_candidates):
	"""Return the first chessboard pattern that can be detected on at least one image."""
	for pattern_size in pattern_candidates:
		for image_path in image_paths:
			image = cv.imread(str(image_path), cv.IMREAD_GRAYSCALE)
			if image is None:
				continue
			found, _ = cv.findChessboardCorners(
				image,
				pattern_size,
				flags=cv.CALIB_CB_ADAPTIVE_THRESH + cv.CALIB_CB_NORMALIZE_IMAGE,
			)
			if found:
				return pattern_size
	return None


def collect_calibration_points(image_paths, pattern_size, square_size=1.0):
	"""Detect chessboard corners and build corresponding object/image point lists."""
	obj_points = []
	img_points = []
	used_images = []
	image_size = None

	criteria = (cv.TERM_CRITERIA_EPS + cv.TERM_CRITERIA_MAX_ITER, 30, 0.001)

	objp = np.zeros((pattern_size[0] * pattern_size[1], 3), np.float32)
	objp[:, :2] = np.mgrid[0 : pattern_size[0], 0 : pattern_size[1]].T.reshape(-1, 2)
	objp *= float(square_size)

	for image_path in image_paths:
		gray = cv.imread(str(image_path), cv.IMREAD_GRAYSCALE)
		if gray is None:
			continue

		found, corners = cv.findChessboardCorners(
			gray,
			pattern_size,
			flags=cv.CALIB_CB_ADAPTIVE_THRESH + cv.CALIB_CB_NORMALIZE_IMAGE,
		)
		if not found:
			continue

		refined = cv.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)
		obj_points.append(objp)
		img_points.append(refined)
		used_images.append(image_path)
		image_size = (gray.shape[1], gray.shape[0])

	return obj_points, img_points, used_images, image_size


def compute_reprojection_error(obj_points, img_points, rvecs, tvecs, camera_matrix, dist_coeffs):
	"""Compute mean reprojection error over all calibration images."""
	total_error = 0.0
	total_points = 0

	for i in range(len(obj_points)):
		projected_points, _ = cv.projectPoints(
			obj_points[i], rvecs[i], tvecs[i], camera_matrix, dist_coeffs
		)
		error = cv.norm(img_points[i], projected_points, cv.NORM_L2)
		total_error += error * error
		total_points += len(obj_points[i])

	if total_points == 0:
		return float("inf")

	return float(np.sqrt(total_error / total_points))


def undistort_and_save_images(image_paths, camera_matrix, dist_coeffs, output_dir):
	"""Undistort all images and save them for visual verification."""
	output_dir.mkdir(parents=True, exist_ok=True)

	for image_path in image_paths:
		image = cv.imread(str(image_path))
		if image is None:
			continue

		h, w = image.shape[:2]
		new_camera_matrix, roi = cv.getOptimalNewCameraMatrix(
			camera_matrix, dist_coeffs, (w, h), 1, (w, h)
		)
		undistorted = cv.undistort(image, camera_matrix, dist_coeffs, None, new_camera_matrix)

		x, y, rw, rh = roi
		if rw > 0 and rh > 0:
			undistorted = undistorted[y : y + rh, x : x + rw]

		out_path = output_dir / f"undist_{image_path.name}"
		cv.imwrite(str(out_path), undistorted)


def calibrate_dataset(dataset_name, dataset_path, pattern_candidates, square_size, output_root):
	image_paths = sorted(
		[p for p in dataset_path.iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png"}]
	)
	if not image_paths:
		raise RuntimeError(f"Dataset '{dataset_name}' neobsahuje obrazky: {dataset_path}")

	pattern_size = find_first_working_pattern(image_paths, pattern_candidates)
	if pattern_size is None:
		raise RuntimeError(
			f"V datasetu '{dataset_name}' se nepodarilo najit sachovnici pro patterny {pattern_candidates}."
		)

	obj_points, img_points, used_images, image_size = collect_calibration_points(
		image_paths, pattern_size, square_size
	)
	if len(obj_points) < 3:
		raise RuntimeError(
			f"Dataset '{dataset_name}' ma malo validnich snimku pro kalibraci ({len(obj_points)})."
		)

	rms, camera_matrix, dist_coeffs, rvecs, tvecs = cv.calibrateCamera(
		obj_points, img_points, image_size, None, None
	)
	reproj_error = compute_reprojection_error(
		obj_points, img_points, rvecs, tvecs, camera_matrix, dist_coeffs
	)

	undistort_and_save_images(used_images, camera_matrix, dist_coeffs, output_root / dataset_name)

	print(f"\n=== {dataset_name.upper()} ===")
	print(f"Pouzity pattern (inner corners): {pattern_size}")
	print(f"Validni snimky: {len(used_images)} / {len(image_paths)}")
	print(f"RMS error (cv.calibrateCamera): {rms:.6f}")
	print(f"Mean reprojection error (pixels): {reproj_error:.6f}")
	print("Camera matrix:")
	print(camera_matrix)
	print("Distortion coeffs:")
	print(dist_coeffs.ravel())

	return camera_matrix, dist_coeffs


def main():
	script_dir = Path(__file__).resolve().parent
	calibration_root = script_dir / "zmd_04_calibration" / "zmd_04_calibration"

	datasets = {
		"phone": calibration_root / "phone_calibration",
		"ueye": calibration_root / "ueye_calibration",
	}

	print("Kalibracni datasety:")
	for name, path in datasets.items():
		print(f"- {name}: {path}")

	output_root = script_dir / "zmd_04_calibration" / "undistorted_output"

	# Common checkerboard candidates from OpenCV calibration tasks.
	pattern_candidates = [(9, 6), (8, 6), (7, 6), (9, 7), (8, 5)]
	square_size = 1.0

	results = {}
	for name, path in datasets.items():
		results[name] = calibrate_dataset(
			dataset_name=name,
			dataset_path=path,
			pattern_candidates=pattern_candidates,
			square_size=square_size,
			output_root=output_root,
		)

	print("\nHotovo.")
	print(f"Narovnane snimky jsou ulozene v: {output_root}")


if __name__ == "__main__":
	main()
