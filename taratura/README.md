# Taratura del Garda (23 novembre 2026)

Confronto tra la visibilità orizzontale misurata dai sub di Project Baseline (stazioni fisse a 22–28 m, 2016–2026)
e la profondità di Secchi da satellite (Sentinel-3, Alplakes) entro 5 giorni. Risultato usato in `index.html`:
`LAKE_SECCHI_TO_HORIZ = 0.9`, `LAKE_VIS_CAP = 14`, forchetta −25% / +25%.

I dati non sono nel repository (termini d'uso di Project Baseline non noti). Per rifare i conti, in questa cartella:

```
for s in Q5 Q6 Q7 Q8 155; do curl -s "https://db.projectbaseline.org/meta.php?station=$s" -o st_$s.json; done
curl -s "https://eawagrs.s3.eu-central-1.amazonaws.com/alplakes/metadata/sentinel3/garda/Zsd_lee.json" -o s3_zsd.json
python serie_secchi.py ts_all.json
python analisi.py
```

Stazioni: Q5 Salò (Lido delle Tavine), Q6 Riva (Porto San Nicolò), 155 Nago-Torbole, Q8 Manerba, Q7 Torri del Benaco.

Risultati principali (74 coppie): visto / Secchi mediana 0,84; sotto 12 m di Secchi 0,91–0,93; d'inverno 0,61 perché
il Secchi sale a 18–20 m mentre i sub vedono 12–14 m. Errore assoluto mediano: 2,1 m con 0,75 × Secchi, 1,5 m con
min(0,9 × Secchi, 14).
