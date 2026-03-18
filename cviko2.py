import numpy as np
import cv2

def demosaic(image_path, output_path):
    """
    Funkce pro demosaicing šedotónového obrázku s Bayerovým filtrem (vzor RGGB).
    Každá chybějící barva v pixelu je vypočítána jako průměr sousedních pixelů
    dané barvy z 3x3 okolí.
    """
    # Načtení šedotónového obrázku
    bayer_img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if bayer_img is None:
        print(f"Chyba: Nelze načíst vstupní obrázek '{image_path}'.")
        return

    h, w = bayer_img.shape
    bayer_img = bayer_img.astype(np.float32)

    # Vytvoření masek pro R, G a B podle zadaného vzoru:
    # R G R G R
    # G B G B G
    # R G R G R
    mask_R = np.zeros((h, w), dtype=np.float32)
    mask_G = np.zeros((h, w), dtype=np.float32)
    mask_B = np.zeros((h, w), dtype=np.float32)

    mask_R[0::2, 0::2] = 1.0    # Sudé řádky, sudé sloupce: R
    mask_G[0::2, 1::2] = 1.0    # Sudé řádky, liché sloupce: G
    mask_G[1::2, 0::2] = 1.0    # Liché řádky, sudé sloupce: G
    mask_B[1::2, 1::2] = 1.0    # Liché řádky, liché sloupce: B

    # Oddělení jednotlivých kanálů (všude jinde budou nuly)
    R = bayer_img * mask_R
    G = bayer_img * mask_G
    B = bayer_img * mask_B

    # Konvoluční jádro definující 8-okolí (3x3 kolem pixelu, bez samotného středu)
    kernel = np.array([[1, 1, 1],
                       [1, 0, 1],
                       [1, 1, 1]], dtype=np.float32)

    def get_interpolated_channel(channel, mask):
        # Součet hodnot dostupných kanálů v okolí
        # cv2.BORDER_CONSTANT zaručí, že mimo obraz se uvažují nuly
        channel_sum = cv2.filter2D(channel, -1, kernel, borderType=cv2.BORDER_CONSTANT)
        
        # Součet masky = zjištění počtu odpovídajících sousedů (řeší tím automaticky okraje a rohy)
        mask_sum = cv2.filter2D(mask, -1, kernel, borderType=cv2.BORDER_CONSTANT)
        
        # Vyhnutí se dělení nulou
        mask_sum[mask_sum == 0] = 1.0
        
        # Výpočet průměru interpolací z okolí
        interpolated = channel_sum / mask_sum
        
        # Na místech kde originální maska má 1.0 si ponecháme originální hodnotu, 
        # jinde použijeme dopočítanou interpolaci z průměrů.
        return np.where(mask == 1.0, channel, interpolated)

    # Vypočtení výsledných kanálů
    R_out = get_interpolated_channel(R, mask_R)
    G_out = get_interpolated_channel(G, mask_G)
    B_out = get_interpolated_channel(B, mask_B)

    # Sloučení R, G, B (OpenCV pro uložení implicitně očekává pole BGR)
    final_img_bgr = np.stack([B_out, G_out, R_out], axis=2)
    final_img_bgr = np.clip(final_img_bgr, 0, 255).astype(np.uint8)

    # Uložení výsledku
    cv2.imwrite(output_path, final_img_bgr)
    print(f"Obrázek zpracován a uložen do: {output_path}")

if __name__ == "__main__":
    # Předpokládáme, že soubor se jmenuje bayer.bmp
    demosaic("bayer.bmp", "output_rgb.bmp")
