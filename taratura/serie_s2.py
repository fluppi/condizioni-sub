"""Serie Sentinel-2 Z490 (Alplakes) vicino a riva, alle stazioni Project Baseline."""
import json, sys, time, urllib.request
API = "https://alplakes-api.eawag.ch"
# punti in acqua a 100-200 m dalla riva davanti alle stazioni
PTS = {"Q6": (45.8725, 10.852), "155": (45.8375, 10.856), "Q5": (45.598, 10.526), "Q8": (45.532, 10.563), "Q7": (45.612, 10.682)}
out = {}
for st, (lat, lon) in PTS.items():
    rows = []
    for y in range(2016, 2027):
        url = f"{API}/remotesensing/timeseries/garda/sentinel2/Z490/{lat}/{lon}/{y}0101/{y}1231?window=2"
        data = None
        for attempt in range(3):
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "condizioni-sub (taratura)", "Accept": "application/json"})
                with urllib.request.urlopen(req, timeout=240) as r: data = json.loads(r.read().decode())
                break
            except Exception as e:
                err = e; time.sleep(3)
        if data is None:
            print(st, y, "ERR", err, flush=True); continue
        for e in data:
            v = e["value"]
            if isinstance(v, dict) and v.get("median") is not None:
                rows.append({"t": e["time"][:10], "v": round(v["median"], 2), "n": v.get("count"), "sd": round(v.get("std") or 0, 2)})
        print(st, y, len(data), flush=True)
    out[st] = rows
json.dump(out, open("ts_s2.json", "w"))
