"""Profili di temperatura del modello Alplakes (dal 2019) nei giorni delle misure Project Baseline."""
import json, sys, time, urllib.request

API = "https://alplakes-api.eawag.ch"
PTS = {"Q6": (45.855, 10.852), "155": (45.835, 10.852), "Q5": (45.600, 10.555), "Q8": (45.535, 10.590), "Q7": (45.612, 10.670)}
out = {}
for st, (lat, lon) in PTS.items():
    vis = json.load(open(f"st_{st}.json"))["visibility"]
    days = sorted({r["time"][:10] for rows in vis.values() for r in rows if r["time"][:10] >= "2019-01-05"})
    out[st] = {}
    for day in days:
        url = f"{API}/simulations/profile/delft3d-flow/garda/{day.replace('-', '')}1200/{lat}/{lon}?variables=temperature"
        p = None
        for attempt in range(3):
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "condizioni-sub (taratura)", "Accept": "application/json"})
                with urllib.request.urlopen(req, timeout=120) as r:
                    p = json.loads(r.read().decode())
                break
            except Exception as e:
                err = e
                time.sleep(2)
        if p is None:
            print(st, day, "ERR", err, file=sys.stderr)
            continue
        pairs = sorted((a, b) for a, b in zip(p["depth"]["data"], p["variables"]["temperature"]["data"]) if a is not None and b is not None and a <= 110)
        out[st][day] = [[round(a, 2), round(b, 2)] for a, b in pairs]
        print(st, day, len(pairs), flush=True)
json.dump(out, open("profili.json", "w"))
