import os
import sys
import json
import time
from playwright.sync_api import sync_playwright

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

COOKIES_PATH = os.path.abspath("cookies.json")


def launch_browser(p):
    for ch in ["msedge", "chrome", None]:
        try:
            kwargs = {"headless": False}
            if ch:
                kwargs["channel"] = ch
            return p.chromium.launch(**kwargs)
        except Exception:
            continue
    return p.chromium.launch(headless=False)


def wait_for_login_and_save():
    print("=" * 60)
    print("[*] ЗАПУСК ОКНА АВТОРИЗАЦИИ СДАМ ГИА...")
    print("[*] Пожалуйста, выполните вход в свой аккаунт в открывшемся окне браузера.")
    print("[*] После успешного входа куки сохранятся автоматически в cookies.json.")
    print("=" * 60)

    with sync_playwright() as p:
        browser = launch_browser(p)
        context = browser.new_context()
        page = context.new_page()

        page.goto("https://math-ege.sdamgia.ru/", wait_until="domcontentloaded")

        print("[*] Ожидаю авторизации (проверка каждые 2 секунды)...")
        logged_in = False
        start_time = time.time()
        timeout = 180  # 3 минуты

        while time.time() - start_time < timeout:
            cookies = context.cookies()
            cookie_names = [c["name"] for c in cookies]

            content = page.content()
            # Проверяем признаки успешного входа
            if "no_user = 1" not in content and ("domain_sid" in cookie_names or "atoken" in cookie_names):
                # Дополнительно проверим наличие блока пользователя
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(content, "html.parser")
                login_div = soup.find("div", class_="login")
                if login_div and "la=login" not in str(login_div):
                    logged_in = True
                    break

            time.sleep(2)

        if logged_in:
            all_cookies = context.cookies()
            with open(COOKIES_PATH, "w", encoding="utf-8") as f:
                json.dump(all_cookies, f, ensure_ascii=False, indent=2)
            print(f"\n[+] УСПЕШНО! Куки сохранены в {COOKIES_PATH}")
            print("[+] Теперь вы можете запускать run_session.py под своим аккаунтом.")
            time.sleep(1)
            browser.close()
            return True
        else:
            print("\n[-] Время ожидания авторизации истекло. Браузер будет закрыт.")
            browser.close()
            return False


if __name__ == "__main__":
    wait_for_login_and_save()
