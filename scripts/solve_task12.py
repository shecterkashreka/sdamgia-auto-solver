# Check all n in [11, 26] and valid d
valid = []
for n in range(11, 27):
    for d in range(0, n + 1):
        if d <= 0.21 * n:
            # new share:
            new_share = (d + 1) / (n + 1) * 100
            if abs(new_share - round(new_share)) < 1e-9:
                p = int(round(new_share))
                valid.append((p, n, d))

valid.sort(reverse=True)
print("Valid integer percentages after new girl joins:")
for p, n, d in valid:
    print(f"p = {p}%: n = {n}, d = {d} (initial share: {d/n*100:.2f}%)")
