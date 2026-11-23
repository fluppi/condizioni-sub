"""Serie puntuali Secchi (Sentinel-3, Alplakes) per i punti al largo delle stazioni Project Baseline."""
import json, sys, time, urllib.request

API = "https://alplakes-api.eawag.ch"
# stazione -> (nome, lat, lon del punto al largo usato per il satellite)
PTS = {
    "Q6": ("Riva", 45.855, 10.852),
    "155": ("Torbole", 45.835, 10.852),
    "Q5": ("Salò", 45.600, 10.555),
    "Q8": ("Manerba", 45.535, 10.590),
    "Q7": ("Torri", 45.612, 10.670),
}
out = {}
for st, (name, lat, lon) in PTS.items():
    rows = []
    for y in range(2016, 2027):
        url = f"{API}/remotesensing/timeseries/garda/sentinel3/Zsd_lee/{lat}/{lon}/{y}0101/{y}1231?window=2"
        for attempt in range(3):
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "condizioni-sub (taratura)", "Accept": "application/json"})
                with urllib.request.urlopen(req, timeout=180) as r:
                    data = json.loads(r.read().decode())
                break
            except Exception as e:
                data = None
                err = e
                time.sleep(2)
        if data is None:
            print(st, y, "ERR", err, file=sys.stderr)
            continue
        for e in data:
            v = e["value"]
            if isinstance(v, dict) and v.get("median") is not None:
                rows.append({"t": e["time"][:10], "v": round(v["median"], 2), "n": v.get("count")})
        print(st, name, y, len(data), flush=True)
    out[st] = rows
json.dump(out, open(sys.argv[1], "w"))
