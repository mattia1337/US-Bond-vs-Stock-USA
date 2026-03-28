# Azioni USA vs Obbligazioni USA — Rendimenti Annuali

Visualizzazioni interattive a scatter-plot dei **rendimenti annuali delle azioni USA vs obbligazioni USA**, anno per anno, su oltre un secolo di storia finanziaria (1910 -- oggi).

Ogni punto del grafico rappresenta un singolo anno solare. L'**asse X** mostra il rendimento annuale delle azioni (S&P 500) e l'**asse Y** mostra il rendimento annuale delle obbligazioni (titoli di Stato USA). I punti sono colorati per decennio e una linea diagonale tratteggiata segna il confine `azioni = obbligazioni`: i punti sopra la linea sono anni in cui le obbligazioni hanno sovraperformato le azioni, i punti sotto sono anni in cui le azioni hanno vinto.

Il repository contiene due implementazioni di questa visualizzazione, costruite con due metodologie e due tecnologie diverse.

---

## Anteprima interattiva

| Grafico | Link |
|---|---|
| **GS10** — Treasury 10 anni, duration 8.5 | [Apri runtime_gs10.html](https://mattia1337.github.io/US-Bond-vs-Stock-USA/runtime_gs10.html) |
| **Ibbotson** — Bond lungo termine, duration 14 | [Apri runtime_ibbotson.html](https://mattia1337.github.io/US-Bond-vs-Stock-USA/runtime_ibbotson.html) |
| **Analisi ML** — Pattern e cicli nei rendimenti | [Apri analysis.html](https://mattia1337.github.io/US-Bond-vs-Stock-USA/analysis.html) |

---

## File di output

### `runtime_gs10.html` — Metodologia "GS10"

Generato a runtime da `us_bonds_vs_stocks.py`. Tutti i dati vengono scaricati in tempo reale da API pubbliche.

| Classe di attività | Fonte | Copertura |
|---|---|---|
| **Azioni** | Yahoo Finance `^GSPC` (rendimento prezzo S&P 500), sovrascritto da `^SP500TR` (rendimento totale S&P 500 con dividendi reinvestiti) dove disponibile | 1928 -- oggi |
| **Obbligazioni** | FRED Moody's AAA (rendimento obbligazioni corporate) come base, sovrascritto da FRED GS10 (rendimento Treasury USA a 10 anni, Constant Maturity) dal 1954 in poi. Il rendimento viene convertito in rendimento totale tramite un **modello di duration con duration modificata = 8.5 anni**, che approssima un Treasury a 10 anni alla pari | 1919 -- oggi |

Questa metodologia utilizza il **Treasury a 10 anni** come benchmark obbligazionario. La duration più breve (8.5) comporta rendimenti obbligazionari meno volatili: le variazioni in conto capitale dovute ai movimenti dei tassi sono più contenute rispetto alla metodologia Ibbotson sotto.

### `runtime_ibbotson.html` — Metodologia "Ibbotson"

Generato a runtime da `us_bonds_vs_stocks.py`. Tutti i dati vengono scaricati in tempo reale da API pubbliche.

| Classe di attività | Fonte | Copertura |
|---|---|---|
| **Azioni** | Shiller/Yale `ie_data.xls` rendimento totale S&P Composite (prezzo mensile + dividendi, capitalizzati annualmente), sovrascritto da Yahoo Finance `^SP500TR` dal 1988 in poi | 1910 -- oggi |
| **Obbligazioni** | Shiller/Yale GS10 come base, sovrascritto da FRED GS30 (rendimento Treasury USA a 30 anni) dal 1977 in poi. Il rendimento viene convertito in rendimento totale tramite un **modello di duration con duration modificata = 14 anni**, che approssima un titolo di Stato a lungo termine 20-30 anni (in linea con la convenzione Ibbotson SBBI) | 1910 -- oggi |

Questa metodologia rispecchia il classico dataset **Ibbotson SBBI (Stocks, Bonds, Bills, and Inflation)** pubblicato da Morningstar. La duration più lunga (14) produce rendimenti obbligazionari più volatili: forti plusvalenze quando i tassi scendono, forti perdite quando salgono. È la stessa convenzione utilizzata nella maggior parte dei libri di testo di finanza accademica.

### `us-bonds-vs-stocks.jsx` — Componente React (Dati Statici)

Componente React standalone che utilizza [Recharts](https://recharts.org/) con **dati hardcoded** da Ibbotson SBBI / Morningstar e stime della Cowles Commission (1910--2024). Nessun download di dati a runtime.

Funzionalità:
- Hover interattivo con tooltip personalizzato che mostra anno, rendimento azionario e rendimento obbligazionario
- Pulsanti filtro per decennio per mostrare/nascondere singoli decenni
- Striscia di statistiche in tempo reale (rendimenti medi, miglior/peggior anno, anni in cui entrambe le classi di attività sono state negative)
- Tema scuro, layout responsive

Note sui dati del JSX:
- **1910--1925**: stime della Cowles Commission / NBER, non dati ufficiali Ibbotson
- **1926--2024**: dati ufficiali Ibbotson SBBI / Morningstar
- Azioni = rendimento totale S&P 500 (dividendi reinvestiti)
- Obbligazioni = rendimento totale dei titoli di Stato USA a lungo termine

### `analysis.html` — Analisi ML e Pattern

Generato da `us_bonds_vs_stocks_analysis.py`. Pagina interattiva con 6 analisi statistiche e di machine learning sul dataset Ibbotson (1910--oggi), pensata per essere comprensibile anche da chi non ha un background finanziario.

Ogni sezione include una spiegazione introduttiva, un grafico interattivo e una conclusione con i risultati chiave.

Le 6 analisi:

1. **Regimi di Mercato (GMM)** — Un algoritmo di machine learning (Gaussian Mixture Model) identifica automaticamente 4 "stati" ricorrenti del mercato: *Goldilocks* (entrambi positivi), *Fuga verso la qualità* (azioni giù, bond su — gli investitori scappano dal rischio e comprano titoli di Stato), *Boom con tassi in salita* (azioni su, bond giù), *Stagflazione/Crisi* (entrambi negativi). Le zone sfumate mostrano la dispersione di ogni regime.

2. **Matrice di Transizione Markov** — Dato il quadrante di quest'anno, qual è la probabilità di finire in ciascun quadrante l'anno prossimo? Le crisi raramente si ripetono due anni di fila.

3. **Correlazione Rolling Azioni-Bond** — Una finestra mobile di 10 anni mostra come cambia nel tempo la relazione tra azioni e obbligazioni. L'area verde indica periodi in cui la diversificazione funziona (bond proteggono dai crolli azionari), l'area rossa indica periodi in cui non funziona (entrambi scendono insieme). Il cambio storico intorno al 2000 e il ritorno della correlazione positiva nel 2022 sono i risultati più importanti.

4. **CAPE come Predittore** — Il rapporto P/E ciclico di Robert Shiller (premio Nobel) confrontato con i rendimenti reali dei 10 anni successivi. Poiché serve aspettare 10 anni per conoscere il rendimento effettivo, gli anni recenti (dopo il ~2015) non hanno ancora un risultato verificabile: i diamanti arancioni li mostrano posizionati sulla previsione storica. I punti sono colorati per decade e cliccabili singolarmente nella legenda.

5. **Mean Reversion** — Dopo un anno di crollo (azioni sotto -10%), cosa succede l'anno dopo? I box plot mostrano che storicamente il rendimento mediano successivo è sopra la media, ma con alta dispersione. Include una previsione per l'anno in corso basata su come ha chiuso l'anno precedente e i precedenti storici comparabili.

6. **Autocorrelazione e Cicli** — I rendimenti passati predicono quelli futuri? I grafici mostrano che per le azioni la risposta è quasi sempre no (mercati efficienti), mentre per le obbligazioni c'è una lieve persistenza legata ai trend pluriennali dei tassi d'interesse.

```bash
python us_bonds_vs_stocks_analysis.py
```

---

## Come funziona il modello di duration obbligazionaria

Poiché i dati sui rendimenti (yield) delle obbligazioni sono ampiamente disponibili, ma i dati sul *rendimento totale* non lo sono (soprattutto per i periodi storici), questo progetto approssima i rendimenti totali obbligazionari a partire dai rendimenti usando il **modello di duration** standard:

```
rendimento(t) = yield(t-1) - duration × (yield(t) - yield(t-1))
```

Dove:
- `yield(t-1)` è il rendimento dell'obbligazione alla fine dell'anno precedente (il reddito da "cedola" incassato)
- `duration × (yield(t) - yield(t-1))` è la plusvalenza o minusvalenza approssimata dovuta alla variazione dei tassi di interesse
- `duration` è la duration modificata dell'obbligazione (8.5 per un Treasury a 10 anni, 14 per un titolo di Stato a lungo termine 20-30 anni)

Quando i tassi **scendono**, gli obbligazionisti incassano la cedola *più* una plusvalenza. Quando i tassi **salgono**, la minusvalenza compensa parzialmente o totalmente il reddito da cedola.

---

## Come usare

### Script Python (`us_bonds_vs_stocks.py`)

**Requisiti**: Python 3.9+

1. Installare le dipendenze:

```bash
pip install -r requirements.txt
```

2. Eseguire lo script:

```bash
python us_bonds_vs_stocks.py
```

3. Lo script:
   - Scaricherà tutti i dati a runtime da Shiller/Yale, FRED e Yahoo Finance
   - Stamperà output diagnostico con copertura e statistiche per ogni fonte dati
   - Genererà due file HTML nella directory corrente: `runtime_gs10.html` e `runtime_ibbotson.html`

4. Aprire i file HTML in un qualsiasi browser. I grafici sono interattivi (basati su [Plotly](https://plotly.com/)): passare il mouse su un punto per vedere l'anno e i rendimenti esatti, cliccare sulle voci della legenda per attivare/disattivare i decenni.

### Componente React (`us-bonds-vs-stocks.jsx`)

Il file JSX è un componente React autonomo progettato per essere inserito in qualsiasi progetto React che utilizza Recharts:

```bash
npm install recharts
```

Poi importare e renderizzare il componente:

```jsx
import App from "./us-bonds-vs-stocks";

// Renderizzare <App /> nella propria app React
```

Non è necessario alcun download di dati: il dataset è incorporato direttamente nel file.

---

## Fonti dati

| Fonte | URL | Cosa fornisce |
|---|---|---|
| **Robert Shiller / Yale** | http://www.econ.yale.edu/~shiller/data/ie_data.xls | Prezzi mensili S&P Composite, dividendi e rendimento GS10 (1871--oggi) |
| **FRED GS10** | https://fred.stlouisfed.org/series/GS10 | Tasso Treasury a 10 anni Constant Maturity, mensile (1953--oggi) |
| **FRED GS30** | https://fred.stlouisfed.org/series/GS30 | Tasso Treasury a 30 anni Constant Maturity, mensile (1977--oggi) |
| **FRED AAA** | https://fred.stlouisfed.org/series/AAA | Rendimento Moody's Seasoned Aaa Corporate Bond, mensile (1919--oggi) |
| **Yahoo Finance** | `^SP500TR` / `^GSPC` tramite [yfinance](https://github.com/ranaroussi/yfinance) | Indice S&P 500 Total Return (1988--oggi) e Indice S&P 500 Price (1927--oggi) |

---

## Licenza

Questo progetto è distribuito sotto la [GNU General Public License v3.0](LICENSE).
