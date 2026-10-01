import math
import numpy as np

def test_root(x):
    denom = math.cos(x) + 1
    if abs(denom) < 1e-9:
        return False
    num = math.cos(2*x)*math.cos(8*x) - math.cos(10*x)
    return abs(num) < 1e-9

print("Testing roots in [0, pi]:")
for n in range(0, 9):
    x = n * math.pi / 8
    denom = math.cos(x) + 1
    if abs(denom) < 1e-9:
        print(f"n={n}, x={n}pi/8: DENOMINATOR ZERO (excluded)")
    else:
        val = test_root(x)
        print(f"n={n}, x={n}pi/8: {val}")
