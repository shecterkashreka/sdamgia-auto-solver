import scipy.optimize as opt
import numpy as np

# We want to maximize min(A1 + x, (40 - A1) + y) + min(...) = 2 * min(A, N)
# with 0 <= A1 <= 40, x >= 0, y >= 0, x^2 + y^2 <= 200

def objective(vars):
    A1, x, y = vars
    A = A1 + x
    N = (40 - A1) + y
    alloy = 2 * min(A, N)
    return -alloy

res = opt.minimize(
    objective,
    [20, 10, 10],
    bounds=[(0, 40), (0, 20), (0, 20)],
    constraints=[{'type': 'ineq', 'fun': lambda v: 200 - v[1]**2 - v[2]**2}]
)

print("Optimal vars (A1, x, y):", res.x)
print("Max alloy:", -res.fun)
