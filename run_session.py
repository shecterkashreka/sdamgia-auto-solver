import os
import sys
import time
import json
import argparse
import re
import shutil
import urllib.parse
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def load_cookies(cookies_path=None):
    """
    Загрузка сессионных куки авторизации.
    Проверяются указанный путь, локальный 'cookies.json' или переменные окружения.
    """
    candidates = []
    if cookies_path:
        candidates.append(cookies_path)
    candidates.append("cookies.json")

    for cp in candidates:
        if os.path.exists(cp):
            try:
                with open(cp, "r", encoding="utf-8") as cf:
                    cookies_data = json.load(cf)
                if cookies_data:
                    print(f"[+] Успешно загружены куки авторизации из: {os.path.abspath(cp)}")
                    clean_cookies = []
                    for c in cookies_data:
                        cookie = {
                            'name': c['name'],
                            'value': c['value'],
                            'domain': c.get('domain'),
                            'path': c.get('path', '/'),
                        }
                        if 'secure' in c:
                            cookie['secure'] = bool(c['secure'])
                        if 'httpOnly' in c:
                            cookie['httpOnly'] = bool(c['httpOnly'])
                        if 'expirationDate' in c:
                            cookie['expires'] = float(c['expirationDate'])
                        elif 'expires' in c:
                            cookie['expires'] = float(c['expires'])
                        same_site = c.get('sameSite', '')
                        if same_site:
                            s = str(same_site).capitalize()
                            if s in ('Strict', 'Lax', 'None'):
                                cookie['sameSite'] = s
                        clean_cookies.append(cookie)
                    return clean_cookies
            except Exception as e:
                print(f"[-] Ошибка чтения {cp}: {e}")

    print("[!] Предупреждение: cookies.json не найден. Для авторизованной сдачи создайте его по шаблону cookies.example.json или запустите scripts/save_session_cookies.py.")
    return []


def clean_cache(work_dir=None):
    """
    Очистка временных файлов кэша.
    """
    targets = [os.path.abspath("cache")]
    if work_dir:
        targets.append(os.path.abspath(os.path.join(work_dir, "cache")))

    cleaned = set()
    for d in targets:
        if os.path.exists(d) and d not in cleaned:
            cleaned.add(d)
            try:
                for item in os.listdir(d):
                    item_path = os.path.join(d, item)
                    if os.path.isfile(item_path) or os.path.islink(item_path):
                        os.unlink(item_path)
                    elif os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                print(f"[+] Кэш успешно очищен: {d}")
            except Exception as e:
                print(f"[-] Ошибка при очистке кэша ({d}): {e}")


def cleanup_temporary_files(work_dir=None, answers_file=None, clean_cache_dirs=True):
    """
    Безопасная автоматическая очистка временных файлов после завершения работы (блок finally):
    1. Очистка папок cache/ и files/;
    2. Удаление файла answers.json;
    3. Рекурсивное удаление служебных папок __pycache__ и файлов *.pyc, *.pyo.

    СТРОГО СОХРАНЯЮТСЯ:
    - Папка screenshots/ и файлы снимков (before_submission.png, submission_result.png);
    - Рабочие файлы скриптов и шаблонов.
    """
    try:
        # 1. Очистка папок cache/ и files/
        if clean_cache_dirs:
            folder_targets = [
                os.path.abspath("cache"),
                os.path.abspath("files")
            ]
            if work_dir:
                folder_targets.append(os.path.abspath(os.path.join(work_dir, "cache")))
                folder_targets.append(os.path.abspath(os.path.join(work_dir, "files")))

            cleaned_folders = set()
            for folder in folder_targets:
                if folder in cleaned_folders:
                    continue
                cleaned_folders.add(folder)
                try:
                    if os.path.exists(folder) and os.path.isdir(folder):
                        for item in os.listdir(folder):
                            if item == ".gitkeep":
                                continue
                            item_path = os.path.join(folder, item)
                            try:
                                if os.path.isfile(item_path) or os.path.islink(item_path):
                                    os.unlink(item_path)
                                elif os.path.isdir(item_path):
                                    shutil.rmtree(item_path, ignore_errors=True)
                            except Exception:
                                pass
                        print(f"[+] Папка успешно очищена: {folder}")
                except Exception:
                    pass

        # 2. Удаление answers.json
        answer_targets = [
            os.path.abspath("answers.json")
        ]
        if work_dir:
            answer_targets.append(os.path.abspath(os.path.join(work_dir, "answers.json")))
        if answers_file:
            answer_targets.append(os.path.abspath(answers_file))

        cleaned_answers = set()
        for af in answer_targets:
            if af in cleaned_answers:
                continue
            cleaned_answers.add(af)
            try:
                if os.path.exists(af) and os.path.isfile(af):
                    os.remove(af)
                    print(f"[+] Временный файл ответов удалён: {af}")
            except Exception:
                pass

        # 3. Рекурсивное удаление папок __pycache__ и файлов *.pyc, *.pyo
        search_roots = [os.path.abspath(".")]
        if work_dir and os.path.abspath(work_dir) not in search_roots:
            search_roots.append(os.path.abspath(work_dir))

        for root_dir in search_roots:
            try:
                for root, dirs, files in os.walk(root_dir, topdown=False):
                    for f in files:
                        if f.endswith(".pyc") or f.endswith(".pyo"):
                            try:
                                os.remove(os.path.join(root, f))
                            except Exception:
                                pass
                    for d in dirs:
                        if d == "__pycache__":
                            try:
                                shutil.rmtree(os.path.join(root, d), ignore_errors=True)
                            except Exception:
                                pass
            except Exception:
                pass

        print("[+] Автоматическая очистка мусора успешно завершена.")
    except Exception as e:
        print(f"[!] Ошибка при автоматической очистке мусора: {e}")


def extract_tasks_from_soup(soup, base_url="https://sdamgia.ru"):
    """
    Извлечение всех заданий из DOM страницы:
    - data-num, data-id
    - имена полей ввода (.test_inp, answer_*)
    - текст задачи с сохранением формул (alt тегов img) и ссылок на файлы
    """
    prob_divs = soup.find_all("div", class_="prob_maindiv")
    tasks = []

    for i, p in enumerate(prob_divs):
        data_num = p.get("data-num", str(i + 1))
        data_id = p.get("data-id", "")
        
        pbody = p.find("div", class_="pbody")
        if pbody:
            # Заменяем теги изображений формул на их LaTeX / текстовые эквиваленты из alt
            for img in pbody.find_all("img"):
                alt = img.get("alt", "").strip()
                src = img.get("src", "").strip()
                if alt:
                    img.replace_with(f" [{alt}] ")
                elif "/get_file?id=" in src:
                    full_src = urllib.parse.urljoin(base_url, src)
                    img.replace_with(f" [ФАЙЛ: {full_src}] ")
            prob_text = pbody.get_text(separator="\n", strip=True)
        else:
            prob_text = p.get_text(separator="\n", strip=True)

        inputs = p.find_all(["input", "textarea"], class_="test_inp")
        if not inputs:
            inputs = [inp for inp in p.find_all(["input", "textarea"]) if "answer" in inp.get("name", "")]
        input_names = [inp.get("name") for inp in inputs]

        tasks.append({
            "task_index": int(data_num) if data_num.isdigit() else i + 1,
            "data_id": data_id,
            "input_names": input_names,
            "text": prob_text
        })

    return tasks


def get_delay_seconds(delay_str=None, delay_min=None, delay_max=None):
    """
    Расчёт случайной задержки:
    - "20-40" -> 20..40 минут
    - "15-30s" -> 15..30 секунд
    - "1-2h" -> 1..2 часа
    """
    import random
    if delay_str:
        s = str(delay_str).strip().lower()
        multiplier = 60  # по умолчанию минуты
        if s.endswith("s") or s.endswith("сек") or s.endswith("sec"):
            multiplier = 1
            s = re.sub(r'[a-zа-я]+', '', s)
        elif s.endswith("m") or s.endswith("мин") or s.endswith("min"):
            multiplier = 60
            s = re.sub(r'[a-zа-я]+', '', s)
        elif s.endswith("h") or s.endswith("ч") or s.endswith("hour"):
            multiplier = 3600
            s = re.sub(r'[a-zа-я]+', '', s)

        if "-" in s:
            parts = s.split("-")
            low = float(parts[0]) * multiplier
            high = float(parts[1]) * multiplier
        else:
            low = high = float(s) * multiplier
        if low > high:
            low, high = high, low
        return int(random.uniform(low, high))
    elif delay_min is not None or delay_max is not None:
        low = (delay_min if delay_min is not None else 20) * 60
        high = (delay_max if delay_max is not None else 40) * 60
        if low > high:
            low, high = high, low
        return int(random.uniform(low, high))
    return 0


def save_tasks_files(tasks, work_dir="."):
    os.makedirs(work_dir, exist_ok=True)
    target_json = os.path.normpath(os.path.join(work_dir, "tasks.json"))
    target_txt = os.path.normpath(os.path.join(work_dir, "tasks.txt"))
    with open(target_json, "w", encoding="utf-8") as f:
        json.dump(tasks, f, ensure_ascii=False, indent=2)

    with open(target_txt, "w", encoding="utf-8") as f:
        for t in tasks:
            f.write(f"=== ЗАДАНИЕ №{t['task_index']} (Каталог ID: {t['data_id']}) ===\n")
            f.write(f"Поля ввода: {t['input_names']}\n")
            f.write(t["text"] + "\n\n")

    # Дублирование в корень, если work_dir не текущий каталог
    if os.path.abspath(work_dir) != os.path.abspath("."):
        try:
            with open("tasks.json", "w", encoding="utf-8") as f:
                json.dump(tasks, f, ensure_ascii=False, indent=2)
            with open("tasks.txt", "w", encoding="utf-8") as f:
                for t in tasks:
                    f.write(f"=== ЗАДАНИЕ №{t['task_index']} (Каталог ID: {t['data_id']}) ===\n")
                    f.write(f"Поля ввода: {t['input_names']}\n")
                    f.write(t["text"] + "\n\n")
        except Exception:
            pass


def verify_variant_match(page, expected_tasks):
    """
    Защитный модуль: сверка data-id и номеров задач в открытом браузере
    с выгруженным списком expected_tasks.
    Предотвращает случайную сдачу не того варианта при перезагрузках или редиректах.
    """
    print("\n" + "=" * 60)
    print("[*] ПРОВЕРКА СОВПАДЕНИЯ ВАРИАНТА ПЕРЕД ОТПРАВКОЙ...")
    print("=" * 60)

    live_tasks = page.eval_on_selector_all(
        ".prob_maindiv",
        "elements => elements.map(el => ({num: el.getAttribute('data-num'), id: el.getAttribute('data-id')}))"
    )

    if not live_tasks:
        print("[-] ОШИБКА: На странице не найдены задания (.prob_maindiv)!")
        return False

    if len(live_tasks) != len(expected_tasks):
        print(f"[-] ОШИБКА: Количество заданий на странице ({len(live_tasks)}) не совпадает с выгруженным ({len(expected_tasks)})!")
        return False

    mismatches = []
    for exp, live in zip(expected_tasks, live_tasks):
        exp_idx = str(exp["task_index"])
        live_idx = str(live.get("num", ""))
        exp_id = str(exp["data_id"])
        live_id = str(live.get("id", ""))

        if exp_idx != live_idx or exp_id != live_id:
            mismatches.append(f"№{exp_idx}: ожидался ID={exp_id}, на странице №{live_idx} ID={live_id}")

    if mismatches:
        print("[-] КРИТИЧЕСКАЯ ОШИБКА: Обнаружено несовпадение заданий варианта!")
        for m in mismatches[:5]:
            print(f"    - {m}")
        if len(mismatches) > 5:
            print(f"    ... и ещё {len(mismatches) - 5} несовпадений.")
        print("[!] ВНИМАНИЕ: На странице открыт ДРУГОЙ вариант! Отправка отменена для защиты результата.")
        return False

    print(f"[OK] Все {len(live_tasks)} заданий на странице ПОЛНОСТЬЮ СОВПАДАЮТ с выгруженным вариантом!")
    return True


def fill_answers(page, answers_dict):
    """
    Заполнение полей ввода на странице:
    - Одиночные поля (input[name='answer_...'])
    - Составные поля (массивы значений)
    - Редакторы развернутых ответов (Draft.js, math_editor, AJAX /sol_upload)
    """
    inputs = page.locator('[name^="answer_"]')
    count = inputs.count()
    print(f"[*] Найдено {count} стандартных полей ввода на странице.")

    task_inputs = {}
    for i in range(count):
        name = inputs.nth(i).get_attribute("name")
        m = re.match(r"^answer_(\d+)_", name)
        if m:
            t_num = int(m.group(1))
            if t_num not in task_inputs:
                task_inputs[t_num] = []
            task_inputs[t_num].append(name)

    filled_count = 0
    for key, val in answers_dict.items():
        val_str = str(val).strip()

        # 1. Прямое совпадение по имени поля
        if isinstance(key, str) and key.startswith("answer_"):
            sel = f'[name="{key}"]'
            if page.locator(sel).count() > 0:
                page.evaluate("""({sel, val}) => {
                    const el = document.querySelector(sel);
                    if (el) {
                        el.value = val;
                        el.style.border = '3px solid #28a745';
                        el.dispatchEvent(new Event('input', { bubbles: true }));
                        el.dispatchEvent(new Event('change', { bubbles: true }));
                    }
                }""", {"sel": sel, "val": val_str})
                filled_count += 1
                continue

        # 2. По номеру задания
        try:
            t_idx = int(key)
        except ValueError:
            continue

        if t_idx in task_inputs:
            names = task_inputs[t_idx]
            if isinstance(val, list):
                for sub_name, sub_val in zip(names, val):
                    sel = f'[name="{sub_name}"]'
                    page.evaluate("""({sel, val}) => {
                        const el = document.querySelector(sel);
                        if (el) {
                            el.value = val;
                            el.style.border = '3px solid #28a745';
                            el.dispatchEvent(new Event('input', { bubbles: true }));
                            el.dispatchEvent(new Event('change', { bubbles: true }));
                        }
                    }""", {"sel": sel, "val": str(sub_val).strip()})
                    filled_count += 1
            elif len(names) == 1:
                sel = f'[name="{names[0]}"]'
                page.evaluate("""({sel, val}) => {
                    const el = document.querySelector(sel);
                    if (el) {
                        el.value = val;
                        el.style.border = '3px solid #28a745';
                        el.dispatchEvent(new Event('input', { bubbles: true }));
                        el.dispatchEvent(new Event('change', { bubbles: true }));
                    }
                }""", {"sel": sel, "val": val_str})
                filled_count += 1
            else:
                parts = val_str.split()
                for sub_name, sub_val in zip(names, parts):
                    sel = f'[name="{sub_name}"]'
                    page.evaluate("""({sel, val}) => {
                        const el = document.querySelector(sel);
                        if (el) {
                            el.value = val;
                            el.style.border = '3px solid #28a745';
                            el.dispatchEvent(new Event('input', { bubbles: true }));
                            el.dispatchEvent(new Event('change', { bubbles: true }));
                        }
                    }""", {"sel": sel, "val": str(sub_val).strip()})
                    filled_count += 1

        # 3. Редакторы развернутых решений (Часть 2 / Draft.js / math_editor / /sol_upload)
        paragraphs = "".join([f"<p>{line}</p>" for line in val_str.split("\n") if line])
        page.evaluate("""({num, val, htmlVal}) => {
            const probDiv = document.querySelector(`[data-num="${num}"]`);
            if (probDiv) {
                const pv = probDiv.closest('.prob_view');
                if (pv) {
                    // 1. txt_editor (Draft.js React editor)
                    const txtTa = pv.querySelector('.txt_editor textarea');
                    if (txtTa) {
                        if (txtTa.react_editor && typeof txtTa.react_editor.setValue === 'function') {
                            txtTa.react_editor.setValue(htmlVal);
                        } else {
                            txtTa.value = val;
                        }
                        txtTa.dispatchEvent(new Event('input', { bubbles: true }));
                        txtTa.dispatchEvent(new Event('change', { bubbles: true }));
                    }

                    // 2. math_editor textarea
                    const mathTa = pv.querySelector('textarea.math_editor');
                    if (mathTa) {
                        mathTa.value = val;
                        mathTa.dispatchEvent(new Event('input', { bubbles: true }));
                        mathTa.dispatchEvent(new Event('change', { bubbles: true }));
                    }

                    // 3. Backend auto-save via AJAX /sol_upload
                    const probId = (txtTa && txtTa.getAttribute('data-prob')) || (mathTa && mathTa.getAttribute('data-prob'));
                    if (probId && window.jQuery) {
                        window.jQuery.post('/sol_upload?a=upload_html&prob=' + probId, {html: val});
                    }
                }
            }
        }""", {"num": str(t_idx), "val": val_str, "htmlVal": paragraphs})

    print(f"[+] Успешно заполнено полей на странице: {filled_count}")
    return filled_count


def launch_browser(p, headless=False):
    """
    Кроссплатформенный запуск Chromium/Edge.
    Пробует поочередно msedge -> chrome -> встроенный chromium.
    """
    channels = ["msedge", "chrome", None]
    last_err = None
    for ch in channels:
        try:
            kwargs = {"headless": headless}
            if ch:
                kwargs["channel"] = ch
            return p.chromium.launch(**kwargs)
        except Exception as e:
            last_err = e
            continue
    raise RuntimeError(f"Не удалось запустить браузер Chromium: {last_err}")


def run(url, trial=False, auto_submit=False, answers_file=None, test_dir=None, delay=None, delay_min=None, delay_max=None, clean_cache_flag=True, headless=False):
    print("=" * 60)
    mode_text = "ПРОБНЫЙ ТЕСТ (TRIAL - без отправки)" if trial else "РАБОЧИЙ РЕЖИМ (ЕДИНАЯ СЕССИЯ)"
    print(f"Запуск сессии: {mode_text}")
    print("=" * 60)

    # Определение рабочей папки теста (изоляция для многозадачности)
    test_id = None
    m_id = re.search(r'id=(\d+)', url)
    if m_id:
        test_id = m_id.group(1)

    if test_dir:
        work_dir = os.path.normpath(os.path.abspath(test_dir))
    elif test_id:
        work_dir = os.path.normpath(os.path.abspath(os.path.join("tests", test_id)))
    else:
        work_dir = os.path.normpath(os.path.abspath("."))

    work_screenshots = os.path.normpath(os.path.join(work_dir, "screenshots"))
    work_cache = os.path.normpath(os.path.join(work_dir, "cache"))
    os.makedirs(work_screenshots, exist_ok=True)
    os.makedirs(work_cache, exist_ok=True)
    os.makedirs(os.path.normpath(os.path.abspath("screenshots")), exist_ok=True)
    os.makedirs(os.path.normpath(os.path.abspath("cache")), exist_ok=True)

    print(f"[*] Рабочая директория теста: {work_dir}")

    cookies_to_use = load_cookies()

    try:
        with sync_playwright() as p:
            browser = launch_browser(p, headless=headless)
            context = browser.new_context()
            if cookies_to_use:
                context.add_cookies(cookies_to_use)
            page = context.new_page()

            print(f"[+] Открываю тест: {url}")
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            time.sleep(2)

            # Проверка и авто-клик по кнопке "Продолжить решение" (для индивидуальных вариантов)
            continue_btn = page.locator('a:has-text("Продолжить решение"), a[href*="continue="]')
            if continue_btn.count() > 0 and continue_btn.first.is_visible():
                print("[!] Обнаружено окно: 'Вы уже начинали решать этот вариант'.")
                print("[+] Нажимаю 'Продолжить решение', сохраняя текущий вариант...")
                continue_btn.first.click()
                page.wait_for_load_state("domcontentloaded")
                time.sleep(2)

            content = page.content()
            with open(os.path.join(work_cache, "live_test_page.html"), "w", encoding="utf-8") as f:
                f.write(content)

            if "prob_maindiv" not in content:
                print("[-] Ошибка: на странице нет заданий. Проверьте авторизацию в cookies.json или ссылку.")
                if not trial and not headless:
                    input("Нажмите Enter для выхода...")
                browser.close()
                return False

            soup = BeautifulSoup(content, "html.parser")
            tasks = extract_tasks_from_soup(soup, base_url=url)
            save_tasks_files(tasks, work_dir=work_dir)
            print(f"[+] Успешно распознано {len(tasks)} заданий варианта (сохранены в {work_dir}/tasks.txt и tasks.json).")

            # Если это пробный запуск:
            if trial:
                print("\n" + "=" * 60)
                print("[ПРОБНЫЙ ТЕСТ] Проверяем модуль сверки заданий...")
                is_valid = verify_variant_match(page, tasks)
                if is_valid:
                    print("\n[ТЕСТ ПРОЙДЕН УСПЕШНО]:")
                    print("1. Браузер открылся и загрузил страницу.")
                    print("2. Плашка 'Продолжить решение' (при наличии) успешно обработана.")
                    print(f"3. Задания варианта извлечены в папку: {work_dir}")
                    print("4. Защита от подмены варианта активна и работает штатно.")
                    print("5. Отправка НЕ производилась (пробный режим).")
                else:
                    print("\n[!] ОШИБКА ПРИ СВЕРКЕ ВАРИАНТА.")

                time.sleep(2)
                browser.close()
                return is_valid

            # Рабочий режим:
            print("=" * 60, flush=True)
            print("[!] Окно браузера открыто. Сессия зафиксирована.", flush=True)
            print("=" * 60, flush=True)

            # Определение файла ответов
            def get_target_answers_path():
                if answers_file and os.path.exists(answers_file):
                    return os.path.normpath(os.path.abspath(answers_file))
                in_work = os.path.normpath(os.path.abspath(os.path.join(work_dir, "answers.json")))
                if os.path.exists(in_work):
                    return in_work
                if os.path.exists("answers.json"):
                    return os.path.normpath(os.path.abspath("answers.json"))
                return in_work

            target_answers = get_target_answers_path()
            loaded = False
            while not loaded:
                if os.path.exists(target_answers):
                    try:
                        with open(target_answers, "r", encoding="utf-8") as f:
                            answers_data = json.load(f)
                        if answers_data:
                            print(f"\n[+] Обнаружен файл ответов: {target_answers}!", flush=True)

                            # Строгая проверка совпадения варианта
                            if not verify_variant_match(page, tasks):
                                print("[-] ОТПРАВКА ЗАБЛОКИРОВАНА ИЗ-ЗА НЕСОВПАДЕНИЯ ВАРИАНТА!", flush=True)
                                browser.close()
                                return False

                            print("[+] Заполняю поля ответов на странице...", flush=True)
                            fill_answers(page, answers_data)
                            time.sleep(2)

                            # Скриншот до отправки (страница с заполненными ответами)
                            before_shot = os.path.normpath(os.path.abspath(os.path.join(work_screenshots, "before_submission.png")))
                            try:
                                page.screenshot(path=before_shot, full_page=True)
                                root_before = os.path.normpath(os.path.abspath("screenshots/before_submission.png"))
                                if before_shot != root_before:
                                    page.screenshot(path=root_before, full_page=True)
                                print(f"[+] Скриншот заполненных полей (до отправки) сохранён: {before_shot}")
                            except Exception as e:
                                print(f"[-] Не удалось сделать скриншот до отправки: {e}")

                            loaded = True
                            break
                    except Exception as e:
                        print(f"[-] Ошибка чтения {target_answers}: {e}", flush=True)
                if not loaded:
                    print(f"[+] Ожидаю файл {target_answers}...", flush=True)
                    time.sleep(2)

            print("-" * 60)

            # Функция задержки перед отправкой для накрутки времени решения
            def wait_delay_if_configured():
                delay_sec = get_delay_seconds(delay, delay_min, delay_max)
                if delay_sec > 0:
                    mins = delay_sec // 60
                    secs = delay_sec % 60
                    print("\n" + "=" * 60)
                    print(f"[⏳ НАКРУТКА ВРЕМЕНИ]: Установлена случайная задержка: {mins} мин. {secs} сек. ({delay_sec} сек.)")
                    print(f"[*] Браузер остаётся открытым на странице теста для имитации реального решения.")
                    print("=" * 60, flush=True)
                    start_t = time.time()
                    while True:
                        elapsed = int(time.time() - start_t)
                        rem = delay_sec - elapsed
                        if rem <= 0:
                            break
                        if rem > 60 and rem % 60 == 0:
                            print(f"[*] [Таймер теста {test_id or ''}] До отправки осталось: {rem // 60} мин...", flush=True)
                        elif rem <= 60 and rem % 10 == 0:
                            print(f"[*] [Таймер теста {test_id or ''}] До отправки осталось: {rem} сек...", flush=True)
                        time.sleep(min(10, rem))
                    print(f"[+] Время накрутки истекло! Отправляю работу на проверку...", flush=True)

            if auto_submit:
                wait_delay_if_configured()
                print("[+] Включен флаг --auto-submit. Отправляю работу...")
                page.evaluate("submit_form()")
                print("[*] Ожидаю завершения отправки...")
                try:
                    page.wait_for_load_state("networkidle", timeout=15000)
                except Exception:
                    time.sleep(5)
                print("[+] Работа успешно отправлена на сайт СДАМ ГИА!")
                # Скриншоты после отправки
                try:
                    after_shot = os.path.normpath(os.path.abspath(os.path.join(work_screenshots, "after_submission.png")))
                    res_shot = os.path.normpath(os.path.abspath(os.path.join(work_screenshots, "submission_result.png")))
                    page.screenshot(path=after_shot)
                    page.screenshot(path=res_shot)
                    root_res = os.path.normpath(os.path.abspath("submission_result.png"))
                    if res_shot != root_res:
                        page.screenshot(path=root_res)
                    print(f"[+] Скриншот результата (после отправки) сохранён: {res_shot}")
                except Exception as e:
                    print(f"[-] Ошибка при сохранении скриншота результата: {e}")
                time.sleep(3)
                browser.close()
                return True
            else:
                choice = input("\n[?] Все ответы заполнены в браузере! Отправить работу сейчас? (y/n): ")
                if choice.strip().lower() == "y":
                    wait_delay_if_configured()
                    print("[+] Отправляю работу...")
                    page.evaluate("submit_form()")
                    time.sleep(5)
                    try:
                        after_shot = os.path.normpath(os.path.abspath(os.path.join(work_screenshots, "after_submission.png")))
                        res_shot = os.path.normpath(os.path.abspath(os.path.join(work_screenshots, "submission_result.png")))
                        page.screenshot(path=after_shot)
                        page.screenshot(path=res_shot)
                        root_res = os.path.normpath(os.path.abspath("submission_result.png"))
                        if res_shot != root_res:
                            page.screenshot(path=root_res)
                        print(f"[+] Скриншот результата сохранён: {res_shot}")
                    except Exception:
                        pass
                else:
                    print("[!] Работа НЕ отправлена. Вы можете проверить ответы в окне браузера.")

                print("\n[+] Ожидание завершения. Нажмите Enter, чтобы закрыть браузер...")
                input()
                browser.close()
                return True
    finally:
        if not trial:
            cleanup_temporary_files(work_dir=work_dir, answers_file=answers_file, clean_cache_dirs=clean_cache_flag)
        elif clean_cache_flag:
            clean_cache(work_dir)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SDAMGIA Automation: Test extraction, realistic timer & safe submission")
    parser.add_argument("--url", required=True, help="Ссылка на тест Решу ЕГЭ / СДАМ ГИА (например, https://math-ege.sdamgia.ru/test?id=...)")
    parser.add_argument("--trial", action="store_true", help="Запустить пробную выгрузку и проверку без отправки")
    parser.add_argument("--auto-submit", action="store_true", help="Автоматически отправить работу после заполнения")
    parser.add_argument("--answers", default=None, help="Путь к файлу ответов (по умолчанию answers.json)")
    parser.add_argument("--test-dir", default=None, help="Папка для изоляции файлов конкретного теста (например, tests/12345)")
    parser.add_argument("--delay", default=None, help="Случайная задержка перед отправкой: например '20-40' (в мин) или '10-20s' (в сек)")
    parser.add_argument("--delay-min", type=int, default=None, help="Минимальная задержка в минутах")
    parser.add_argument("--delay-max", type=int, default=None, help="Максимальная задержка в минутах")
    parser.add_argument("--no-clean-cache", action="store_true", help="Отключить автоматическое удаление временных файлов кэша")
    parser.add_argument("--headless", action="store_true", help="Запуск в фоновом режиме (без отображения окна браузера)")
    args = parser.parse_args()

    run(
        url=args.url,
        trial=args.trial,
        auto_submit=args.auto_submit,
        answers_file=args.answers,
        test_dir=args.test_dir,
        delay=args.delay,
        delay_min=args.delay_min,
        delay_max=args.delay_max,
        clean_cache_flag=not args.no_clean_cache,
        headless=args.headless
    )
