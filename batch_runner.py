import os
import sys
import argparse
import re
import subprocess
import time

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def extract_urls_from_args(args_list):
    urls = []
    for arg in args_list:
        found = re.findall(r'https?://[a-zA-Z0-9\.\-]+sdamgia\.ru/[^\s"\'<>]+', arg)
        urls.extend(found)
    return list(dict.fromkeys(urls))  # сохраняем порядок, убираем дубли


def get_test_id(url):
    m = re.search(r'id=(\d+)', url)
    return m.group(1) if m else str(abs(hash(url)) % 10000000)


def main():
    parser = argparse.ArgumentParser(description="SDAMGIA Multi-Test Batch Runner with Independent Timers")
    parser.add_argument("raw_args", nargs="*", help="Ссылки на тесты СДАМ ГИА / Решу ЕГЭ")
    parser.add_argument("--trial", action="store_true", help="Запустить пробную выгрузку вариантов для всех тестов")
    parser.add_argument("--auto-submit", action="store_true", help="Запустить отправку с задержкой для каждого теста")
    parser.add_argument("--delay", default="20-40", help="Диапазон случайной задержки в минутах (по умолчанию 20-40)")
    parser.add_argument("--parallel", action="store_true", default=True, help="Запуск отправки в параллельных сессиях")
    parser.add_argument("--headless", action="store_true", help="Запуск браузеров в фоновом режиме")
    parsed_args, unknown = parser.parse_known_args()

    all_inputs = parsed_args.raw_args + unknown
    urls = extract_urls_from_args(all_inputs)

    if not urls:
        print("[-] Ошибка: в аргументах не найдено ссылок на тесты Решу ЕГЭ / СДАМ ГИА.")
        print("Примеры использования:")
        print('  python batch_runner.py https://math-ege.sdamgia.ru/test?id=12345678 --trial')
        print('  python batch_runner.py https://math-ege.sdamgia.ru/test?id=12345678 https://inf-ege.sdamgia.ru/test?id=87654321 --auto-submit --delay 20-40')
        return

    print("=" * 70)
    print(f"[*] СДАМ ГИА: ПАКЕТНЫЙ МУЛЬТИ-ЗАПУСК ({len(urls)} вариантов)")
    print("=" * 70)
    for i, u in enumerate(urls, 1):
        print(f"  {i}. [ID: {get_test_id(u)}] {u}")
    print("=" * 70)

    # 1. Режим пробной выгрузки вариантов (TRIAL)
    if parsed_args.trial or (not parsed_args.auto_submit):
        print("\n[ЭТАП 1: Выгрузка всех вариантов и создание изолированных папок...]")
        for i, url in enumerate(urls, 1):
            t_id = get_test_id(url)
            t_dir = os.path.join("tests", t_id)
            os.makedirs(t_dir, exist_ok=True)
            print(f"\n---> [{i}/{len(urls)}] Выгружаю тест ID {t_id} в папку {t_dir}...")
            cmd = [
                sys.executable, "-u", "run_session.py",
                "--url", url,
                "--test-dir", t_dir,
                "--trial"
            ]
            if parsed_args.headless:
                cmd.append("--headless")
            res = subprocess.run(cmd)
            if res.returncode == 0:
                print(f"[OK] Тест ID {t_id} успешно выгружен в {t_dir}")
            else:
                print(f"[-] Ошибка выгрузки теста ID {t_id} (код: {res.returncode})")

        print("\n" + "=" * 70)
        print("[+] Выгрузка вариантов завершена!")
        print("Теперь сформируйте ответы в соответствующих файлах:")
        for u in urls:
            t_id = get_test_id(u)
            print(f"  - tests/{t_id}/answers.json")
        print("\nПосле подготовки ответов запустите отправку:")
        print(f"  python batch_runner.py {' '.join(urls)} --auto-submit --delay {parsed_args.delay}")
        print("=" * 70)
        return

    # 2. Режим автоматической отправки с отдельными таймерами
    if parsed_args.auto_submit:
        print("\n[ЭТАП 2: Запуск отправки с индивидуальными таймерами накрутки...]")
        processes = []

        for i, url in enumerate(urls, 1):
            t_id = get_test_id(url)
            t_dir = os.path.join("tests", t_id)
            answers_path = os.path.join(t_dir, "answers.json")
            if not os.path.exists(answers_path) and os.path.exists("answers.json"):
                answers_path = "answers.json"

            if not os.path.exists(answers_path):
                print(f"[-] Пропуск теста ID {t_id}: не найден файл ответов {os.path.join(t_dir, 'answers.json')}!")
                continue

            cmd = [
                sys.executable, "-u", "run_session.py",
                "--url", url,
                "--test-dir", t_dir,
                "--answers", answers_path,
                "--auto-submit",
                "--delay", parsed_args.delay
            ]
            if parsed_args.headless:
                cmd.append("--headless")

            print(f"[+] Запуск сессии для теста ID {t_id} с таймером {parsed_args.delay} мин...")
            p = subprocess.Popen(cmd)
            processes.append({
                "id": t_id,
                "url": url,
                "dir": t_dir,
                "process": p
            })
            time.sleep(2)  # Небольшая пауза между стартами браузеров

        print(f"\n[*] Все {len(processes)} сессий запущены параллельно!")
        print(f"[*] У каждого теста активен свой независимый таймер накрутки времени ({parsed_args.delay} мин).")
        print("[*] Ожидаем завершения отправки всех вариантов...")

        # Ожидание завершения всех процессов
        completed = 0
        total = len(processes)
        while completed < total:
            time.sleep(5)
            new_completed = sum(1 for item in processes if item["process"].poll() is not None)
            if new_completed != completed:
                completed = new_completed
                print(f"[*] Прогресс отправки: {completed}/{total} тестов завершено.")

        print("\n" + "=" * 70)
        print("[+] ВСЕ ТЕСТЫ УСПЕШНО ОБРАБОТАНЫ И ОТПРАВЛЕНЫ!")
        print("=" * 70)
        for item in processes:
            res_code = item["process"].returncode
            shot_path = os.path.join(item["dir"], "screenshots", "submission_result.png")
            status = "УСПЕШНО" if res_code == 0 else f"ОШИБКА ({res_code})"
            print(f"- Тест ID {item['id']}: {status}")
            if os.path.exists(shot_path):
                print(f"  Скриншот результата: {shot_path}")


if __name__ == "__main__":
    main()
