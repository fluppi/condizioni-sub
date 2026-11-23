"""Sentinel-2 (Z490, vicino a riva) predice la visibilita' dei sub meglio di Sentinel-3 (Secchi, al largo)?"""
import datetime as dt, json, statistics as st
NAMES = {"Q6": "Riva", "155": "Torbole", "Q5": "Salo", "Q8": "Manerba", "Q7": "Torri"}
s3 = json.load(open("ts_all.json")); s2 = json.load(open("ts_s2.json"))
D = lambda s: dt.date.fromisoformat(s[:10])
def nearest(rows, day, maxd):
    best = None
    for d, v in rows:
        k = abs((d - day).days)
        if k <= maxd and (best is None or k < best[0]): best = (k, v)
    return best
P = []
for stn, name in NAMES.items():
    js = json.load(open(f"st_{stn}.json"))
    a = [(D(r["t"]), r["v"]) for r in s3[stn] if 0.3 < r["v"] < 40 and (r["n"] or 0) >= 3]
    b = [(D(r["t"]), r["v"]) for r in s2[stn] if 0.3 < r["v"] < 40 and (r["n"] or 0) >= 10]
    for depth, rows in js["visibility"].items():
        byday = {}
        for r in rows: byday.setdefault(r["time"][:10], []).append(float(r["value"]))
        for day, vals in byday.items():
            x, y = nearest(a, D(day), 5), nearest(b, D(day), 5)
            if y: P.append({"st": name, "day": day, "vis": st.mean(vals), "s3": x[1] if x else None, "s2": y[1], "age2": y[0]})
print("misure con Sentinel-2 entro 5 giorni:", len(P), "| anche con Sentinel-3:", sum(1 for r in P if r["s3"]))
B = [r for r in P if r["s3"]]
def corr(x, y):
    mx, my = st.mean(x), st.mean(y); sx = sum((a - mx) ** 2 for a in x) ** .5; sy = sum((b - my) ** 2 for b in y) ** .5
    return sum((a - mx) * (b - my) for a, b in zip(x, y)) / (sx * sy)
print("rapporto vista/Z490 (S2): mediana %.2f | vista/Secchi (S3): mediana %.2f" % (st.median([r["vis"] / r["s2"] for r in B]), st.median([r["vis"] / r["s3"] for r in B])))
print("correlazione con la vista: S2 %.2f | S3 %.2f | S2-S3 tra loro %.2f" % (corr([r["s2"] for r in B], [r["vis"] for r in B]), corr([r["s3"] for r in B], [r["vis"] for r in B]), corr([r["s2"] for r in B], [r["s3"] for r in B])))
def ev(f):
    e = [f(r) - r["vis"] for r in B]
    return "mediano %.2f medio %.2f bias %+.2f" % (st.median([abs(x) for x in e]), st.mean([abs(x) for x in e]), st.mean(e))
k2 = st.median([r["vis"] / r["s2"] for r in B])
print("S3 attuale min(0,9 S,14):", ev(lambda r: min(0.9 * r["s3"], 14)))
for cap in (12, 14, 99): print(f"S2 {k2:.2f} x Z490, tetto {cap}:", ev(lambda r, cap=cap: min(k2 * r["s2"], cap)))
print("media dei due:", ev(lambda r: (min(0.9 * r["s3"], 14) + min(k2 * r["s2"], 14)) / 2))
for r in sorted(B, key=lambda r: r["day"])[-14:]: print("  ", r["day"], f"{r['st']:<8} vista {r['vis']:>5.1f}  S3 {r['s3']:>5.1f}  S2 {r['s2']:>5.1f}")
