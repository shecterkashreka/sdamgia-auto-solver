import zipfile
import sys
import xml.etree.ElementTree as ET

sys.stdout.reconfigure(encoding="utf-8")

import os
import glob

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
files_dir = os.path.join(base_dir, "files")

ods_path = sys.argv[1] if len(sys.argv) > 1 else None
if not ods_path:
    matches = glob.glob(os.path.join(files_dir, "*3*.ods"))
    if matches:
        ods_path = matches[0]
    else:
        ods_path = os.path.join(files_dir, "3.ods")

with zipfile.ZipFile(ods_path) as z:
    tree = ET.fromstring(z.read("content.xml"))

ns = {
    "table": "urn:oasis:names:tc:opendocument:xmlns:table:1.0",
    "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0"
}

data = {}
for table in tree.iterfind(".//table:table", ns):
    tname = table.get(f"{{{ns['table']}}}name")
    rows_data = []
    for row in table.iterfind("table:table-row", ns):
        row_vals = []
        for cell in row.iterfind("table:table-cell", ns):
            rep = int(cell.get(f"{{{ns['table']}}}number-columns-repeated", "1"))
            if rep > 50:
                continue
            p_texts = [p.text or "" for p in cell.iterfind(".//text:p", ns)]
            val = " ".join(p_texts).strip()
            for _ in range(rep):
                row_vals.append(val)
        if any(row_vals):
            rows_data.append(row_vals)
    data[tname] = rows_data
    print(f"Table {tname}: {len(rows_data)} rows")

# 1. Спектакли: 'все драмы М. А. Булгакова'
spectacles = data["Спектакли"]
bulgakov_drama_codes = set()
for r in spectacles[1:]:
    code, name, author, director, genre = r[0], r[1], r[2], r[3], r[4]
    if "Булгаков" in author and "драма" in genre.lower():
        bulgakov_drama_codes.add(code)
        print(f"Matching spectacle: Code={code}, Name={name}, Author={author}, Genre={genre}")

# 2. Цены: 'по тарифу утреннего или вечернего спектакля летнего сезона'
tariffs = data["Цены"]
matching_tariffs = {}
for r in tariffs[1:]:
    t_id, t_name, p_adult, p_disc, p_child = r[0], r[1], r[2], r[3], r[4]
    name_lower = t_name.lower()
    if "лет" in name_lower and ("утр" in name_lower or "вечер" in name_lower):
        matching_tariffs[t_id] = float(p_child.replace(",", "."))
        print(f"Matching tariff: ID={t_id}, Name={t_name}, ChildPrice={p_child}")

# 3. Продажа_билетов
sales = data["Продажа_билетов"]
total_child_sum = 0
matching_rows = 0

for r in sales[1:]:
    op_id, d_buy, t_buy, spec_code, t_id, d_spec, q_adult, q_disc, q_child = r[:9]
    if spec_code in bulgakov_drama_codes and t_id in matching_tariffs:
        count = int(q_child) if q_child.isdigit() else 0
        price = matching_tariffs[t_id]
        total_child_sum += count * price
        matching_rows += 1

print(f"Total matching sales rows: {matching_rows}")
print(f"TOTAL CHILD SUM: {int(total_child_sum)}")
