import sys
import json
import os
import re
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding="utf-8")

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
default_candidates = [
    os.path.join(base_dir, "cache", "live_test_page.html"),
    os.path.join(base_dir, "cache", "test_page.html"),
    os.path.join(base_dir, "test_page.html"),
]

html_path = sys.argv[1] if len(sys.argv) > 1 else None
if not html_path:
    for c in default_candidates:
        if os.path.exists(c):
            html_path = c
            break

if not html_path or not os.path.exists(html_path):
    print(f"[-] HTML файл не найден. Ожидался в cache/live_test_page.html или укажите путь аргументом.")
    sys.exit(1)

with open(html_path, "r", encoding="utf-8") as f:
    soup = BeautifulSoup(f.read(), "html.parser")

prob_divs = soup.find_all("div", class_="prob_maindiv")

for i, p in enumerate(prob_divs):
    data_id = p.get("data-id")
    print(f"\n=== ЗАДАНИЕ №{i+1} (data-id: {data_id}) ===")
    
    # Text snippet
    pbody = p.find("div", class_="pbody")
    text = pbody.get_text(separator=" ", strip=True) if pbody else p.get_text(separator=" ", strip=True)
    print("Текст:", text[:200] + ("..." if len(text) > 200 else ""))
    
    # Links (files)
    for a in p.find_all("a"):
        href = a.get("href")
        if href and not href.startswith("javascript"):
            print(f"  Файл/Ссылка: {a.get_text(strip=True)} -> {href}")
            
    # Images
    for img in p.find_all("img"):
        src = img.get("src")
        if src and not src.startswith("data:"):
            print(f"  Картинка: {src}")
