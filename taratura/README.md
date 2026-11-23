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

## Due strati: sopra e sotto il salto termico (23 novembre 2026)

Per le 96 misure dal 2019 (65 con il Secchi del satellite entro 5 giorni) si è scaricato il profilo di temperatura
del modello Alplakes di quel giorno (`python profili.py`, poi `python strati.py` e `python fit_strati.py`).

| Salto di temperatura tra 1 m e la quota del sub | Misure | Vista / Secchi |
|---|---|---|
| meno di 0,5 °C (stessa acqua della superficie) | 26 | 0,71 |
| da 0,5 a 2 °C | 18 | 0,91 |
| oltre 2 °C (sotto il salto termico) | 21 | 1,26 (tra 0,98 e 1,31 secondo la metà dei dati usata) |

In `index.html`: `lakeK` = 0,71 / 0,9 / 1,1 con tetto a 14 m. A 25 m non è più precisa di min(0,9 × Secchi, 14)
(errore medio 2,0 m contro 2,1; su metà dei dati tenuta da parte è pari o peggiore), quindi il guadagno non è la
precisione ma il secondo numero: quanto si vede nell'altro strato. Le misure sono tutte a 22–28 m: sotto i 30 m è
un'estrapolazione.
