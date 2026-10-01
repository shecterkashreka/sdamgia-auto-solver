import os
import sys
import glob
import zipfile
import xml.etree.ElementTree as ET

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
files_dir = os.path.join(base_dir, "files")

ods_path = sys.argv[1] if len(sys.argv) > 1 else None
if not ods_path:
    matches = glob.glob(os.path.join(files_dir, "*9*.ods"))
    if matches:
        ods_path = matches[0]
    else:
        ods_path = os.path.join(files_dir, "09.ods")

with zipfile.ZipFile(ods_path) as z:
    tree = ET.fromstring(z.read("content.xml"))

ns = {
    "table": "urn:oasis:names:tc:opendocument:xmlns:table:1.0",
    "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0"
}

rows = []
for row in tree.iterfind(".//table:table-row", ns):
    row_vals = []
    for cell in row.iterfind("table:table-cell", ns):
        rep = int(cell.get(f"{{{ns['table']}}}number-columns-repeated", "1"))
        if rep > 50:
            continue
        p_texts = [p.text or "" for p in cell.iterfind(".//text:p", ns)]
        val = " ".join(p_texts).strip()
        for _ in range(rep):
            if val != "":
                row_vals.append(val)
    if len(row_vals) >= 8:
        try:
            nums = [int(v) for v in row_vals[:8]]
            rows.append(nums)
        except ValueError:
            pass

print(f"Total parsed rows with 8 numbers: {len(rows)}")
print("Sample row:", rows[0])

matching_count = 0
for row in rows:
    avg = sum(row) / len(row)
    
    # заметные: строго больше среднего арифметического
    prominent = [x for x in row if x > avg]
    prom_even = sum(1 for x in prominent if x % 2 == 0)
    prom_odd = sum(1 for x in prominent if x % 2 != 0)
    
    cond1 = (prom_even < prom_odd)
    
    # сумма всех чётных > суммы всех нечётных
    sum_even = sum(x for x in row if x % 2 == 0)
    sum_odd = sum(x for x in row if x % 2 != 0)
    
    cond2 = (sum_even > sum_odd)
    
    if cond1 and cond2:
        matching_count += 1

print("Task 9 answer:", matching_count)
