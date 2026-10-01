import re
import math

def analyze_task_3():
    with open('files/task_3_165335.png', 'r', encoding='utf-8') as f:
        content = f.read()

    # Find the main curve path
    # Look around stroke="#CC761F"
    idx = content.find('stroke="#CC761F"')
    while idx != -1:
        start_d = content.find(' d="', idx - 200)
        if start_d != -1:
            end_d = content.find('"', start_d + 4)
            d_val = content[start_d + 4:end_d]
            print(f"Path near {idx}: {d_val[:100]}...")
            # parse path
            # The path starts at M460.8491,21.4729
            # Then has relative cubic bezier curves 'c dx1,dy1 dx2,dy2 dx,dy'
            # Let's reconstruct absolute coordinates!
            cur_x, cur_y = 0, 0
            tokens = re.findall(r'([a-zA-Z])|([-\d\.]+)', d_val)
            # Reconstruct points
        idx = content.find('stroke="#CC761F"', idx + 1)

analyze_task_3()
