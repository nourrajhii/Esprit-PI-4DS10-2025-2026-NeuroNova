import requests
from bs4 import BeautifulSoup
import re

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'fr-FR,fr;q=0.9'
}

cat_url = "https://www.comaf.tn/73-ciment-et-produits-en-beton.html"
print(f"Chargement : {cat_url}")

resp = requests.get(cat_url, headers=headers, timeout=15)
soup = BeautifulSoup(resp.text, 'html.parser')

product_url = None
for a in soup.find_all('a', href=True):
    href = a['href']
    if '.html' in href and 'comaf.tn' in href and '/73-' not in href:
        product_url = href
        break

print(f"Produit : {product_url}\n")

if product_url:
    resp2 = requests.get(product_url, headers=headers, timeout=15)
    soup2 = BeautifulSoup(resp2.text, 'html.parser')

    print("=== CLASSES price/prix ===")
    for tag in soup2.find_all(True):
        classes = ' '.join(tag.get('class', []))
        tag_id = tag.get('id', '')
        if any(kw in (classes + tag_id).lower() for kw in ['price', 'prix', 'tarif']):
            print(f"  <{tag.name} class='{classes}' id='{tag_id}'> -> '{tag.text.strip()[:80]}'")

    print("\n=== TEXTE AVEC DT/TND ===")
    text = soup2.get_text(separator='\n')
    for line in text.split('\n'):
        line = line.strip()
        if line and re.search(r'\d.*(?:dt|tnd)', line, re.I):
            print(f"  {line[:100]}")

    print("\n=== JSON-LD ===")
    for script in soup2.find_all('script', type='application/ld+json'):
        print(script.string[:500] if script.string else "vide")