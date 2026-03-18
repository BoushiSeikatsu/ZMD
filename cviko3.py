import cv2
import numpy as np

def compute_hdr(image_paths, mu=0.5, sigma=0.2):
    images = [cv2.imread(p).astype(np.float32) for p in image_paths]
    
    if any(img is None for img in images):
        print("Error loading some images. Ensure s1_0.png through s1_4.png are in the directory.")
        return
    
    weights = []
    for img in images:
        # Převedeme na černobílý obrázek (luminanci) pro výpočet vah
        gray = cv2.cvtColor(img.astype(np.uint8), cv2.COLOR_BGR2GRAY).astype(np.float32)
        
        # Calculate weights according to the formula, ale pouze na jasu
        # Tím zamezíme posunům barev (color shift), protože všechny RGB kanály
        # daného pixelu dostanou stejnou váhu
        weight = np.exp(-((gray - 255 * mu) ** 2) / (2 * (255 * sigma) ** 2))
        
        # Rozšíření dimenze pro následné násobení s RGB (H, W, 1)
        weight = np.expand_dims(weight, axis=2)
        weights.append(weight)
        
    weights = np.array(weights)
    images = np.array(images)
    
    # Normalize weights so that sum of w_k = 1 for each pixel
    weight_sum = np.sum(weights, axis=0)
    # Avoid division by zero
    weight_sum[weight_sum == 0] = 1e-8
    
    normalized_weights = weights / weight_sum
    
    # Compute the final radiance
    hdr_image = np.sum(normalized_weights * images, axis=0)
    
    # Convert to 8-bit image for saving/displaying
    hdr_image = np.clip(hdr_image, 0, 255).astype(np.uint8)
    
    return hdr_image

if __name__ == "__main__":
    image_files = [f"s1_{i}.png" for i in range(5)]
    hdr_result = compute_hdr(image_files)
    
    if hdr_result is not None:
        cv2.imwrite("hdr_output.png", hdr_result)
        print("HDR image saved as hdr_output.png")
