import math

# For a given R = |a|:
# Circle: u^2 + y^2 = R^2
# Square: |u| + |y| = 4

# Let's find all intersection points (u, y):
# Since |u| + |y| = 4, let |u| = t, |y| = 4 - t, with 0 <= t <= 4.
# Then u^2 + y^2 = t^2 + (4 - t)^2 = 2t^2 - 8t + 16 = R^2.
# 2t^2 - 8t + (16 - R^2) = 0.
# Discriminant: D_t = 64 - 8(16 - R^2) = 8R^2 - 64 = 8(R^2 - 8).

# For R^2 >= 8 (R >= 2*sqrt(2)):
# t = (8 +- sqrt(8(R^2 - 8))) / 4 = 2 +- sqrt(2(R^2 - 8)) / 2 = 2 +- sqrt((R^2 - 8)/2).

# Let's write a function to count the total number of solutions (x, y) for a given R:
def count_solutions(R):
    if R <= 0:
        return 0, 0
    disc = 8 * R**2 - 64
    if disc < -1e-9:
        return 0, 0
    elif abs(disc) < 1e-9:
        t_vals = [2.0]
    else:
        sq = math.sqrt((R**2 - 8) / 2)
        t1 = 2.0 - sq
        t2 = 2.0 + sq
        t_vals = []
        if 0 <= t1 <= 4:
            t_vals.append(t1)
        if 0 <= t2 <= 4 and abs(t2 - t1) > 1e-9:
            t_vals.append(t2)
            
    # For each t in t_vals:
    # t = |u|, so u = t or u = -t (if t > 0, 2 values of u; if t == 0, 1 value u = 0)
    # y: |y| = 4 - t. If 4 - t > 0, 2 values of y (+-); if 4 - t == 0, 1 value y = 0.
    
    # Let's collect all unique pairs (u, y):
    pairs = set()
    for t in t_vals:
        u_list = [t, -t] if t > 1e-9 else [0.0]
        y_abs = 4.0 - t
        y_list = [y_abs, -y_abs] if y_abs > 1e-9 else [0.0]
        for u in u_list:
            for y in y_list:
                pairs.add((round(u, 8), round(y, 8)))
                
    # Now count solutions (x, y)
    total_xy = 0
    for u, y in pairs:
        # 2x - x^2 = u => x^2 - 2x + u = 0
        D_x = 4 - 4*u
        if D_x > 1e-9:
            total_xy += 2
        elif abs(D_x) <= 1e-9:
            total_xy += 1
        else:
            total_xy += 0
            
    return len(pairs), total_xy

print("R in range [2*sqrt(2), 4]:")
for r_int in range(282, 401, 1):
    R = r_int / 100.0
    n_pairs, n_xy = count_solutions(R)
    if n_xy == 8:
        print(f"R = {R:.2f}: pairs={n_pairs}, xy_solutions={n_xy}")
