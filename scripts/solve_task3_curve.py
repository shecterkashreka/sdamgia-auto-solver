import re
import sys
sys.stdout.reconfigure(encoding='utf-8')
import numpy as np

# Path:
d = """M460.8491,21.4729c-7.4375,19.2002-12.8506,41.7798-20.1006,59.9917c-3.1465,7.9043-8.459,14.9497-11.4033,20.6001
c-9.7256,18.667-21.8096,33.1709-29.127,39.8262c-11.3447,10.3184-22.791-5.4033-28.7207-8.627
c-10.9893-5.9746-13.8213,30.7734-20.5625,27.4473c-6.7402-3.3262-13.5664-35.6309-20.0498-47.6523
c-6.4854-12.0186-13.8232-12.6992-18.7734-24.6353c-4.9482-11.9341-7.5928-35.8848-10.9199-46.9673
c-3.3281-11.0815-5.8867-17.7305-9.1299-19.4355c-3.2422-1.7056-6.9111,3.4106-10.4092,9.291
c-3.498,5.8833-6.3975,19.0103-10.75,25.9146c-4.3516,6.9028-11.5176,9.2056-15.5303,15.3447
c-4.0088,6.1372-4.6055,9.9712-8.7012,21.3081c-4.0947,11.3398-10.1543,36.9121-15.8672,46.8018
c-5.7197,9.8877-13.3145,13.9785-18.1758,12.4434c-4.8652-1.5332-7.6328-20.0918-11.1289-31.7715
c-3.502-11.6777-6.1055-24.3184-9.6914-38.5527c-3.584-14.2368-6.2285-26.8521-11.6025-36.9985
c-5.377-10.1426-13.9951-19.7744-20.3936-23.7808c-6.3979-4.0059-12.2021-2.0464-17.918,0"""

x0 = 261.311
y0 = 81.3723
step = 19.969

# Parse M
m_match = re.match(r'M([-\d\.]+),([-\d\.]+)', d)
start_x = float(m_match.group(1))
start_y = float(m_match.group(2))

# Find all 'c' chunks
c_chunks = re.split(r'[cM]', d)[2:] # after M and empty

sampled_points = []

curr_x, curr_y = start_x, start_y

# Actually re.findall to get all cubic segments:
# Each cubic has dx1,dy1 dx2,dy2 dx,dy
numbers = [float(x) for x in re.findall(r'[-+]?\d*\.?\d+', d)[2:]]
print(f"Total numbers in c: {len(numbers)} (should be multiple of 6: {len(numbers)/6})")

for i in range(0, len(numbers), 6):
    dx1, dy1 = numbers[i], numbers[i+1]
    dx2, dy2 = numbers[i+2], numbers[i+3]
    dx, dy = numbers[i+4], numbers[i+5]
    
    p0 = np.array([curr_x, curr_y])
    p1 = p0 + np.array([dx1, dy1])
    p2 = p0 + np.array([dx2, dy2])
    p3 = p0 + np.array([dx, dy])
    
    for t in np.linspace(0, 1, 100):
        pt = (1-t)**3 * p0 + 3*(1-t)**2 * t * p1 + 3*(1-t) * t**2 * p2 + t**3 * p3
        # Convert to math coords:
        mx = (pt[0] - x0) / step
        my = (y0 - pt[1]) / step # positive y is above x-axis
        sampled_points.append((mx, my))
        
    curr_x, curr_y = p3[0], p3[1]

# Sort points by math x
sampled_points.sort(key=lambda p: p[0])

print(f"X range: {sampled_points[0][0]:.2f} to {sampled_points[-1][0]:.2f}")

# Find value of f'(x) at integer points x from -5 to 9
print("\nValues of f'(x) at integer x:")
for int_x in range(-5, 10):
    # interpolate y at int_x
    # find closest points
    pts = [p for p in sampled_points if abs(p[0] - int_x) < 0.05]
    if pts:
        avg_y = sum(p[1] for p in pts) / len(pts)
        print(f"x = {int_x:2d}: f'(x) = {avg_y:+6.2f} -> {'f >= 0 (возрастает)' if avg_y >= -0.01 else 'f < 0 (убывает)'}")

# Find zero crossings:
print("\nZero crossings of f'(x):")
for i in range(len(sampled_points)-1):
    x1, y1 = sampled_points[i]
    x2, y2 = sampled_points[i+1]
    if (y1 <= 0 and y2 >= 0) or (y1 >= 0 and y2 <= 0):
        # linear interpolation
        if abs(y2 - y1) > 1e-6:
            xz = x1 - y1 * (x2 - x1) / (y2 - y1)
            print(f"Zero at x ≈ {xz:.3f} (going {'up' if y2 > y1 else 'down'})")
