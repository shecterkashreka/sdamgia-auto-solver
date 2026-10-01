import os
import sys
import glob
import zipfile
import xml.etree.ElementTree as ET

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
files_dir = os.path.join(base_dir, "files")

ods_path = sys.argv[1] if len(sys.argv) > 1 else None
if not ods_path:
    matches = glob.glob(os.path.join(files_dir, "*18*.ods"))
    if matches:
        ods_path = matches[0]
    else:
        ods_path = os.path.join(files_dir, "18 (2).ods")

with zipfile.ZipFile(ods_path) as z:
    tree = ET.fromstring(z.read("content.xml"))

ns = {
    "table": "urn:oasis:names:tc:opendocument:xmlns:table:1.0",
    "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0"
}

grid = []
for row in tree.iterfind(".//table:table-row", ns):
    row_vals = []
    for cell in row.iterfind("table:table-cell", ns):
        rep = int(cell.get(f"{{{ns['table']}}}number-columns-repeated", "1"))
        if rep > 100:
            continue
        p_texts = [p.text or "" for p in cell.iterfind(".//text:p", ns)]
        val = " ".join(p_texts).strip()
        for _ in range(rep):
            row_vals.append(val)
    if any(row_vals):
        grid.append(row_vals)

print(f"Raw grid size: {len(grid)} rows, {len(grid[0]) if grid else 0} cols")

# Convert cells to int
board = []
for r in grid:
    row_nums = []
    for val in r:
        try:
            row_nums.append(int(val))
        except ValueError:
            pass
    if row_nums:
        board.append(row_nums)

H = len(board)
W = len(board[0])
print(f"Board size: {H} rows x {W} cols")
print("Top-left:", board[0][0], "Bottom-left:", board[H-1][0])

# Robot starts at LEFT-BOTTOM corner:
# In spreadsheet indexing: row = H - 1, col = 0.
# Move right: col + 1 (same row)
# Move up: row - 1 (same col)
# Blocked cell: board[r][c] == -1

# Let's find all reachable cells and min energy to each cell.
# Energy to start = board[H - 1][0].
# Energy to move from (r, c) to (nr, nc) = abs(board[nr][nc] - board[r][c]).

# Since moves are only UP and RIGHT (row decreases, col increases), this is a DAG!
# Let's compute min_cost[r][c] to reach each cell (r, c) from (H - 1, 0).
inf = float('inf')
min_cost = [[inf] * W for _ in range(H)]

start_r = H - 1
start_c = 0
min_cost[start_r][start_c] = board[start_r][start_c]

# Iterate from bottom to top, left to right
for r in range(H - 1, -1, -1):
    for c in range(W):
        if min_cost[r][c] == inf or board[r][c] == -1:
            continue
        curr_cost = min_cost[r][c]
        curr_val = board[r][c]
        
        # move RIGHT: (r, c + 1)
        if c + 1 < W and board[r][c + 1] != -1:
            step_cost = abs(board[r][c + 1] - curr_val)
            if curr_cost + step_cost < min_cost[r][c + 1]:
                min_cost[r][c + 1] = curr_cost + step_cost
                
        # move UP: (r - 1, c)
        if r - 1 >= 0 and board[r - 1][c] != -1:
            step_cost = abs(board[r - 1][c] - curr_val)
            if curr_cost + step_cost < min_cost[r - 1][c]:
                min_cost[r - 1][c] = curr_cost + step_cost

# Final cells:
# 'Клетка, из которой робот не может сделать допустимого хода (справа и сверху находятся границы поля или запрещённые клетки), называется финальной.'
# Let's check which REACHABLE cells are final!
final_costs = []
all_finals = []

for r in range(H):
    for c in range(W):
        if board[r][c] != -1:
            can_right = (c + 1 < W and board[r][c + 1] != -1)
            can_up = (r - 1 >= 0 and board[r - 1][c] != -1)
            if not can_right and not can_up:
                all_finals.append((r, c))
                if min_cost[r][c] != inf:
                    final_costs.append(min_cost[r][c])

print(f"Total final cells: {len(all_finals)}, Reachable final cells: {len(final_costs)}")
print(f"Final costs: {sorted(final_costs)}")

# Задание 1: минимальный начальный запас энергии, который позволит роботу добраться до какой-нибудь финальной клетки = min(final_costs)
# Задание 2: минимальный начальный запас энергии, который позволит роботу добраться до ЛЮБОЙ финальной клетки = max(final_costs)
ans1 = min(final_costs)
ans2 = max(final_costs)
print(f"Answer 1: {ans1}")
print(f"Answer 2: {ans2}")
