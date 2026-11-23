import json, statistics as st
R = [r for r in json.load(open("strati.json")) if r["S"]]
for r in R: r["dT"] = max(0.0, r["T1"] - r["Tmod"])
def ev(f, rows=R):
    e = [f(r) - r["vis"] for r in rows]
    return st.median([abs(x) for x in e]), st.mean([abs(x) for x in e]), st.mean(e), sum(1 for r in rows if 0.75 * f(r) <= r["vis"] <= 1.25 * f(r)) / len(rows)
def show(name, f):
    a, b, c, d = ev(f); print(f"{name:<52} mediano {a:.2f}  medio {b:.2f}  bias {c:+.2f}  dentro ±25%: {d:.0%}")
print("coppie:", len(R))
show("attuale: min(0,9·S, 14)", lambda r: min(0.9 * r["S"], 14))
show("solo 0,72·S", lambda r: 0.72 * r["S"])
best = None
for k in [x / 100 for x in range(60, 86, 2)]:
    for g in [x / 100 for x in range(0, 51, 5)]:
        for cap_dt in (2, 3, 4, 5):
            for cap in (14, 16, 99):
                f = lambda r, k=k, g=g, c=cap_dt, cap=cap: min(k * r["S"] * (1 + g * min(r["dT"], c)), cap)
                m = ev(f)
                key = (round(m[1], 3), round(m[0], 3))
                if best is None or key < best[0]: best = (key, k, g, cap_dt, cap)
print("migliore (errore medio):", best)
_, k, g, c, cap = best
show(f"migliore: min({k}·S·(1+{g}·min(dT,{c})), {cap})", lambda r: min(k * r["S"] * (1 + g * min(r["dT"], c)), cap))
for kk, gg, cc, cp in ((0.72, 0.25, 3, 14), (0.70, 0.25, 3, 14), (0.72, 0.20, 3, 14), (0.75, 0.20, 3, 14), (0.72, 0.25, 3, 99)):
    show(f"min({kk}·S·(1+{gg}·min(dT,{cc})), {cp})", lambda r, kk=kk, gg=gg, cc=cc, cp=cp: min(kk * r["S"] * (1 + gg * min(r["dT"], cc)), cp))
# stabilità: tarare su anni pari, provare sui dispari e viceversa
for lab, tr, te in (("pari-su-dispari", 0, 1), ("dispari-su-pari", 1, 0)):
    A = [r for r in R if int(r["day"][:4]) % 2 == tr]; B = [r for r in R if int(r["day"][:4]) % 2 == te]
    bb = None
    for k in [x / 100 for x in range(60, 86, 2)]:
        for g in [x / 100 for x in range(0, 51, 5)]:
            f = lambda r, k=k, g=g: min(k * r["S"] * (1 + g * min(r["dT"], 3)), 14)
            m = ev(f, A)[1]
            if bb is None or m < bb[0]: bb = (m, k, g)
    f = lambda r: min(bb[1] * r["S"] * (1 + bb[2] * min(r["dT"], 3)), 14)
    print(lab, "k", bb[1], "g", bb[2], "| prova: nuovo medio %.2f mediano %.2f" % (ev(f, B)[1], ev(f, B)[0]), "| attuale medio %.2f mediano %.2f" % (ev(lambda r: min(0.9 * r["S"], 14), B)[1], ev(lambda r: min(0.9 * r["S"], 14), B)[0]), "n", len(B))
