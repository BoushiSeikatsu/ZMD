# Task 1: RGB to YUV Image Converter

## Popis úkolu
Jednoduchý konvertor obrazu, kde na vstupu je RGB obraz, který se převede do YUV reprezentace a následně zpět do RGB obrazu. Tento postup je podobný tomu, co se dělo v analogovém TV vysílání.

## Implementace
Konverze jsou realizovány pomocí maticových operací s využitím NumPy.

## Použité transformační matice

### RGB → YUV (ITU-R BT.601)
```
Y =  0.299*R + 0.587*G + 0.114*B
U = -0.147*R - 0.289*G + 0.436*B
V =  0.615*R - 0.515*G - 0.100*B
```

### YUV → RGB (inverzní transformace)
```
R = Y + 1.140*V
G = Y - 0.395*U - 0.581*V
B = Y + 2.032*U
```

## Použití

### Instalace závislostí
```bash
pip install -r requirements.txt
```

### Spuštění
```bash
python task1.py
```

## Výsledky

Program vytváří:
1. **Testovací obraz** - barevné pruhy (červená, žlutá, zelená, cyan, modrá, magenta)
2. **YUV reprezentaci** - oddělené Y, U, V kanály
3. **Rekonstruovaný RGB obraz** - zpětná konverze z YUV
4. **Vizualizaci** - porovnání všech kroků konverze
5. **Metriky kvality** - PSNR a rozdíly mezi původním a rekonstruovaným obrazem

### Typické výsledky
- **PSNR**: ~56 dB (velmi kvalitní rekonstrukce)
- **Maximální rozdíl**: ~1 pixel (z 255)
- **Průměrný rozdíl**: ~0.17 pixel

## Výstupní soubory
- `original_rgb.png` - původní RGB obraz
- `reconstructed_rgb.png` - rekonstruovaný RGB obraz
- `conversion_visualization.png` - kompletní vizualizace všech kroků

## Bezpečnost
Všechny závislosti jsou aktualizované a bez známých bezpečnostních zranitelností.
