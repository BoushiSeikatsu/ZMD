"""
Task 1: RGB to YUV Image Converter
Konverze RGB obrazu do YUV reprezentace a zpět do RGB pomocí maticových operací.
"""

import numpy as np
from PIL import Image
import matplotlib.pyplot as plt


def rgb_to_yuv(rgb_image):
    """
    Konverze RGB obrazu do YUV reprezentace pomocí maticové operace.
    
    Args:
        rgb_image: numpy array ve formátu (height, width, 3) s hodnotami 0-255
        
    Returns:
        yuv_image: numpy array ve formátu (height, width, 3) s YUV hodnotami
    """
    # Normalizace RGB hodnot do rozsahu 0-1
    rgb_normalized = rgb_image.astype(np.float64) / 255.0
    
    # Transformační matice RGB -> YUV (ITU-R BT.601)
    # Y =  0.299*R + 0.587*G + 0.114*B
    # U = -0.147*R - 0.289*G + 0.436*B
    # V =  0.615*R - 0.515*G - 0.100*B
    transform_matrix = np.array([
        [ 0.299,  0.587,  0.114],
        [-0.147, -0.289,  0.436],
        [ 0.615, -0.515, -0.100]
    ])
    
    # Reshape pro maticové násobení
    height, width, channels = rgb_normalized.shape
    rgb_reshaped = rgb_normalized.reshape(-1, 3)
    
    # Maticová operace: YUV = RGB * transform_matrix^T
    yuv_reshaped = np.dot(rgb_reshaped, transform_matrix.T)
    
    # Reshape zpět
    yuv_image = yuv_reshaped.reshape(height, width, 3)
    
    return yuv_image


def yuv_to_rgb(yuv_image):
    """
    Konverze YUV obrazu zpět do RGB reprezentace pomocí maticové operace.
    
    Args:
        yuv_image: numpy array ve formátu (height, width, 3) s YUV hodnotami
        
    Returns:
        rgb_image: numpy array ve formátu (height, width, 3) s hodnotami 0-255
    """
    # Inverzní transformační matice YUV -> RGB
    # R = Y + 1.140*V
    # G = Y - 0.395*U - 0.581*V
    # B = Y + 2.032*U
    inverse_transform_matrix = np.array([
        [1.000,  0.000,  1.140],
        [1.000, -0.395, -0.581],
        [1.000,  2.032,  0.000]
    ])
    
    # Reshape pro maticové násobení
    height, width, channels = yuv_image.shape
    yuv_reshaped = yuv_image.reshape(-1, 3)
    
    # Maticová operace: RGB = YUV * inverse_transform_matrix^T
    rgb_reshaped = np.dot(yuv_reshaped, inverse_transform_matrix.T)
    
    # Reshape zpět
    rgb_normalized = rgb_reshaped.reshape(height, width, 3)
    
    # Oříznutí hodnot do rozsahu 0-1 a konverze zpět na 0-255
    rgb_clipped = np.clip(rgb_normalized, 0, 1)
    rgb_image = (rgb_clipped * 255).astype(np.uint8)
    
    return rgb_image


def create_test_image(width=400, height=300):
    """
    Vytvoření testovacího barevného obrazu.
    
    Args:
        width: Šířka testovacího obrazu (default: 400)
        height: Výška testovacího obrazu (default: 300)
    
    Returns:
        test_image: numpy array s RGB testovacím obrazem
    """
    test_image = np.zeros((height, width, 3), dtype=np.uint8)
    
    # Vytvoření barevných pruhů
    stripe_width = width // 6
    
    # Červená
    test_image[:, 0:stripe_width, :] = [255, 0, 0]
    # Žlutá
    test_image[:, stripe_width:2*stripe_width, :] = [255, 255, 0]
    # Zelená
    test_image[:, 2*stripe_width:3*stripe_width, :] = [0, 255, 0]
    # Cyan
    test_image[:, 3*stripe_width:4*stripe_width, :] = [0, 255, 255]
    # Modrá
    test_image[:, 4*stripe_width:5*stripe_width, :] = [0, 0, 255]
    # Magenta
    test_image[:, 5*stripe_width:, :] = [255, 0, 255]
    
    return test_image


def calculate_psnr(original, reconstructed):
    """
    Vypočítá Peak Signal-to-Noise Ratio (PSNR) mezi dvěma obrazy.
    """
    mse = np.mean((original.astype(np.float64) - reconstructed.astype(np.float64)) ** 2)
    if mse == 0:
        return float('inf')
    max_pixel = 255.0
    psnr = 20 * np.log10(max_pixel / np.sqrt(mse))
    return psnr


def visualize_conversion(original_rgb, yuv_image, reconstructed_rgb):
    """
    Vizualizace původního RGB, YUV kanálů a rekonstruovaného RGB obrazu.
    """
    fig, axes = plt.subplots(2, 3, figsize=(15, 10))
    
    # Původní RGB obraz
    axes[0, 0].imshow(original_rgb)
    axes[0, 0].set_title('Původní RGB obraz')
    axes[0, 0].axis('off')
    
    # Y kanál (luminance)
    axes[0, 1].imshow(yuv_image[:, :, 0], cmap='gray', vmin=0, vmax=1)
    axes[0, 1].set_title('Y kanál (luminance)')
    axes[0, 1].axis('off')
    
    # U kanál (chrominance)
    axes[0, 2].imshow(yuv_image[:, :, 1], cmap='RdBu', vmin=-0.5, vmax=0.5)
    axes[0, 2].set_title('U kanál (chrominance)')
    axes[0, 2].axis('off')
    
    # V kanál (chrominance)
    axes[1, 0].imshow(yuv_image[:, :, 2], cmap='RdBu', vmin=-0.5, vmax=0.5)
    axes[1, 0].set_title('V kanál (chrominance)')
    axes[1, 0].axis('off')
    
    # Rekonstruovaný RGB obraz
    axes[1, 1].imshow(reconstructed_rgb)
    axes[1, 1].set_title('Rekonstruovaný RGB obraz')
    axes[1, 1].axis('off')
    
    # Rozdíl mezi původním a rekonstruovaným
    difference = np.abs(original_rgb.astype(np.float64) - reconstructed_rgb.astype(np.float64))
    axes[1, 2].imshow(difference.astype(np.uint8))
    axes[1, 2].set_title(f'Rozdíl (max: {np.max(difference):.2f})')
    axes[1, 2].axis('off')
    
    plt.tight_layout()
    plt.savefig('conversion_visualization.png', dpi=150, bbox_inches='tight')
    print("Vizualizace uložena jako 'conversion_visualization.png'")
    plt.close()


def main():
    """
    Hlavní funkce demonstrující RGB -> YUV -> RGB konverzi.
    """
    print("=" * 60)
    print("RGB to YUV Image Converter - Task 1")
    print("=" * 60)
    
    # Vytvoření testovacího obrazu
    print("\n1. Vytváření testovacího obrazu...")
    test_image = create_test_image()
    print(f"   Rozměry: {test_image.shape}")
    print(f"   Rozsah hodnot: {test_image.min()} - {test_image.max()}")
    
    # Konverze RGB -> YUV
    print("\n2. Konverze RGB -> YUV...")
    yuv_image = rgb_to_yuv(test_image)
    print(f"   YUV rozměry: {yuv_image.shape}")
    print(f"   Y rozsah: {yuv_image[:,:,0].min():.3f} - {yuv_image[:,:,0].max():.3f}")
    print(f"   U rozsah: {yuv_image[:,:,1].min():.3f} - {yuv_image[:,:,1].max():.3f}")
    print(f"   V rozsah: {yuv_image[:,:,2].min():.3f} - {yuv_image[:,:,2].max():.3f}")
    
    # Konverze YUV -> RGB
    print("\n3. Konverze YUV -> RGB...")
    reconstructed_rgb = yuv_to_rgb(yuv_image)
    print(f"   RGB rozměry: {reconstructed_rgb.shape}")
    print(f"   Rozsah hodnot: {reconstructed_rgb.min()} - {reconstructed_rgb.max()}")
    
    # Výpočet rozdílu
    print("\n4. Analýza přesnosti rekonstrukce...")
    difference = np.abs(test_image.astype(np.float64) - reconstructed_rgb.astype(np.float64))
    print(f"   Průměrný rozdíl: {np.mean(difference):.4f}")
    print(f"   Maximální rozdíl: {np.max(difference):.4f}")
    print(f"   PSNR: {calculate_psnr(test_image, reconstructed_rgb):.2f} dB")
    
    # Vizualizace
    print("\n5. Vytváření vizualizace...")
    visualize_conversion(test_image, yuv_image, reconstructed_rgb)
    
    # Uložení obrazů
    print("\n6. Ukládání obrazů...")
    Image.fromarray(test_image).save('original_rgb.png')
    print("   - original_rgb.png")
    Image.fromarray(reconstructed_rgb).save('reconstructed_rgb.png')
    print("   - reconstructed_rgb.png")
    
    print("\n" + "=" * 60)
    print("Konverze dokončena!")
    print("=" * 60)


if __name__ == "__main__":
    main()
