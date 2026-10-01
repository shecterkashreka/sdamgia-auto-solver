import os
import sys
import glob
import zipfile
import xml.etree.ElementTree as ET

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
files_dir = os.path.join(base_dir, "files")

ods_path = sys.argv[1] if len(sys.argv) > 1 else None
if not ods_path:
    matches = glob.glob(os.path.join(files_dir, "*22*.ods"))
    if matches:
        ods_path = matches[0]
    else:
        ods_path = os.path.join(files_dir, "22.ods")

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
            row_vals.append(val)
    if any(row_vals):
        rows.append(row_vals)

print("Header:", rows[0])

processes = {} # id -> (duration, [dependencies])
for r in rows[1:]:
    try:
        p_id = int(r[0])
        dur = int(r[1])
        deps_raw = r[2] if len(r) > 2 else "0"
        deps = []
        for d in deps_raw.replace(";", " ").replace(",", " ").split():
            if d.strip() and int(d) != 0:
                deps.append(int(d))
        processes[p_id] = (dur, deps)
    except (ValueError, IndexError):
        pass

print(f"Total processes: {len(processes)}")
for p_id, (dur, deps) in sorted(processes.items()):
    print(f"ID {p_id}: dur={dur}, deps={deps}")

# Each process can start as early as max(end_time of deps)
# But wait! Can processes start later?
# 'Определите максимальную длительность отрезка времени (в мс), в течение которого ВОЗМОЖНО одновременное выполнение пяти процессов, при условии, что в эту пятёрку не входит процесс с ID = 6.'
# Note the word: 'ВОЗМОЖНО' (it is possible) or under standard schedule?
# In EGE type 22, processes start as early as possible OR can they be delayed?
# Let's check earliest start / finish times first!
end_times = {}
start_times = {}

def get_end(p_id):
    if p_id in end_times:
        return end_times[p_id]
    dur, deps = processes[p_id]
    if not deps:
        st = 0
    else:
        st = max(get_end(d) for d in deps)
    start_times[p_id] = st
    end_times[p_id] = st + dur
    return st + dur

for p in processes:
    get_end(p)

print("\n--- Earliest Schedule ---")
for p in sorted(processes):
    print(f"Process {p}: [{start_times[p]}, {end_times[p]}]")

# Let's check intervals under earliest schedule
max_t = max(end_times.values())
# For each 1 ms interval [t, t+1]:
active_intervals = []
for t in range(max_t):
    # processes active at time t (excluding process 6)
    active = [p for p in processes if p != 6 and start_times[p] <= t < end_times[p]]
    active_intervals.append(len(active))

# Consecutive ms where >= 5 processes run
max_consec = 0
cur_consec = 0
for count in active_intervals:
    if count >= 5:
        cur_consec += 1
        max_consec = max(max_consec, cur_consec)
    else:
        cur_consec = 0

print(f"Max consecutive duration with >= 5 processes (excluding ID 6) under earliest schedule: {max_consec}")
