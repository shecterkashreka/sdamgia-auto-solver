from bs4 import BeautifulSoup
import urllib.request
import os

"""
Утилита для дампинга условий задач с извлечением формул (из alt-тегов)
и скачиванием графических материалов (диаграммы, схемы) в папку files/.
"""

PAGE_FILE = "live_test_page.html"
if not os.path.exists(PAGE_FILE):
    PAGE_FILE = os.path.join("cache", "live_test_page.html")

if not os.path.exists(PAGE_FILE):
    print(f"[-] Файл страницы не найден ({PAGE_FILE}). Сначала запустите run_session.py --trial.")
    exit(1)

with open(PAGE_FILE, "r", encoding="utf-8") as f:
    soup = BeautifulSoup(f.read(), "html.parser")

probs = soup.find_all("div", class_="prob_maindiv")
os.makedirs("files", exist_ok=True)

with open("tasks_full_text.txt", "w", encoding="utf-8") as out:
    for p in probs:
        num = p.get("data-num")
        pid = p.get("data-id")
        pbody = p.find("div", class_="pbody")
        if not pbody:
            continue
        
        # Заменяем теги картинок на alt формул или скачиваем графики
        for img in pbody.find_all("img"):
            alt = img.get("alt", "")
            src = img.get("src", "")
            if "/get_file?id=" in src:
                file_id = src.split("=")[-1]
                file_name = f"files/task_{num}_{file_id}.png"
                img_url = "https://math-ege.sdamgia.ru" + src
                try:
                    urllib.request.urlretrieve(img_url, file_name)
                    img.replace_with(f" [РИСУНОК {file_name}] ")
                except Exception:
                    img.replace_with(f" [РИСУНОК {src}] ")
            elif alt:
                img.replace_with(f" [{alt}] ")

        text = pbody.get_text(" ", strip=True)
        out.write(f"=== ЗАДАНИЕ №{num} (Каталог ID: {pid}) ===\n")
        out.write(text + "\n\n")

print("[+] Задания сохранены в tasks_full_text.txt, изображения выгружены в files/")
