import math

def f(x):
    if x <= 0.5 or x == 4:
        return None
    lhs = math.log2((4 - x)**2) + 2 * math.log2(2*x - 1)
    rhs = 4 * math.log2(3)
    return lhs <= rhs + 1e-9

# Test values
tests = [0.4, 0.5, 0.51, 1.0, 2.0, 3.99, 4.0, 4.01, 4.5, 5.0, 5.01, 6.0]
for x in tests:
    print(f"x={x}: {f(x)}")
