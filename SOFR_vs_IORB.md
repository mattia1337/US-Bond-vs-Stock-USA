# SOFR vs IORB: Analisi Comparativa dei Tassi Overnight USA

## Introduzione

Il sistema finanziario statunitense si basa su una serie di tassi di interesse a breve termine che determinano il costo del denaro "overnight" (prestiti della durata di una notte). Due dei tassi piu' importanti in questo ecosistema sono il **SOFR** e l'**IORB**, che pur essendo strettamente correlati hanno natura, meccanismi e scopi profondamente diversi.

Questo documento analizza entrambi i tassi, la loro relazione e il grafico che li mette a confronto dal 2018 ad oggi.

---

## Cos'e' il SOFR (Secured Overnight Financing Rate)

### Definizione

Il SOFR e' il **tasso di riferimento per i prestiti overnight garantiti** (secured) nel mercato dei repurchase agreements (repo) degli Stati Uniti. E' calcolato come media ponderata per volume di tutte le transazioni repo overnight collateralizzate da titoli del Tesoro USA.

### Come funziona il mercato Repo

Un'operazione repo funziona cosi':

1. La **Parte A** ha bisogno di liquidita' (cash) per una notte
2. La **Parte A** vende titoli del Tesoro alla **Parte B**, con l'accordo di riacquistarli il giorno dopo a un prezzo leggermente superiore
3. La differenza di prezzo rappresenta l'**interesse** — ovvero il SOFR

In pratica e' un prestito garantito: chi presta denaro detiene titoli governativi come collaterale, il che rende l'operazione a bassissimo rischio.

### Caratteristiche principali

| Caratteristica | Dettaglio |
|---|---|
| **Natura** | Tasso di mercato, osservato dalle transazioni reali |
| **Pubblicazione** | Federal Reserve Bank of New York, ogni giorno lavorativo |
| **Collaterale** | Titoli del Tesoro USA (Treasury) |
| **Volume giornaliero** | Circa 2.000 miliardi di dollari |
| **Partecipanti** | Banche, primary dealer, money market funds, hedge funds |
| **Disponibilita' dati** | Dal 3 aprile 2018 (dati ricostruiti dal 2014) |

### Perche' e' stato creato

Il SOFR e' stato introdotto nel 2018 come **sostituto del LIBOR** (London Interbank Offered Rate), che era stato al centro di uno scandalo di manipolazione. A differenza del LIBOR, che si basava su stime soggettive delle banche, il SOFR si basa su **transazioni reali e verificabili**, con volumi giornalieri nell'ordine dei trilioni di dollari, rendendolo praticamente impossibile da manipolare.

### Utilizzo

Il SOFR e' oggi il tasso di riferimento per:
- Mutui a tasso variabile (ARM - Adjustable Rate Mortgages)
- Prestiti corporate e sindacati
- Derivati su tassi di interesse (swap, futures)
- Obbligazioni a tasso variabile (FRN - Floating Rate Notes)

---

## Cos'e' l'IORB (Interest on Reserve Balances)

### Definizione

L'IORB e' il **tasso di interesse che la Federal Reserve paga alle banche commerciali** sulle riserve che queste detengono presso la Fed. E' un tasso **amministrato**, cioe' fissato direttamente dal Federal Open Market Committee (FOMC) come strumento di politica monetaria.

### Come funziona

Ogni banca commerciale negli USA e' obbligata a mantenere un conto presso la Federal Reserve. Su questo conto la banca deposita le proprie **riserve** — essenzialmente il denaro che la banca tiene "parcheggiato" alla Fed anziche' prestarlo. Dal 2008, la Fed paga un interesse su queste riserve.

### Storia: da IOER/IOER a IORB

| Periodo | Nome | Dettaglio |
|---|---|---|
| **Pre-2008** | Nessun interesse | La Fed non pagava interessi sulle riserve |
| **2008-2021** | **IOER** (Interest on Excess Reserves) e **IORR** (Interest on Required Reserves) | Due tassi separati: uno sulle riserve in eccesso, uno sulle riserve obbligatorie |
| **2021-oggi** | **IORB** (Interest on Reserve Balances) | Unificazione in un unico tasso su tutte le riserve |

La transizione e' avvenuta il 29 luglio 2021, quando la Fed ha eliminato la distinzione tra riserve obbligatorie e in eccesso (gia' resa irrilevante dall'azzeramento dei requisiti di riserva obbligatoria nel marzo 2020).

### Caratteristiche principali

| Caratteristica | Dettaglio |
|---|---|
| **Natura** | Tasso amministrato, fissato dalla Fed |
| **Decisione** | FOMC (Federal Open Market Committee) |
| **Partecipanti** | Solo istituzioni con conto alla Fed (banche commerciali, casse di risparmio) |
| **Funzione** | Strumento di politica monetaria (floor del corridoio dei tassi) |
| **Disponibilita' dati** | Serie IORB dal 29 luglio 2021; serie IOER dal 2008 |

### Perche' esiste

Prima del 2008, la Fed controllava i tassi a breve termine principalmente attraverso operazioni di mercato aperto (comprando/vendendo Treasury). Dopo la crisi finanziaria del 2008, con l'esplosione delle riserve bancarie causata dal Quantitative Easing (QE), questo meccanismo tradizionale non funzionava piu'.

L'IORB serve come **ancora per i tassi a breve termine**: se la Fed paga il 4.40% sulle riserve, nessuna banca prestera' denaro a un tasso inferiore nel mercato interbancario — perche' puo' semplicemente "parcheggiare" i soldi alla Fed senza rischio. Questo crea un **pavimento** (floor) sotto i tassi di mercato.

---

## La Relazione tra SOFR e IORB

### Il corridoio dei tassi della Fed

La Federal Reserve gestisce i tassi a breve termine attraverso un "corridoio" (corridor system):

```
Tasso di sconto (Discount Rate)          <-- Soffitto (ceiling)
     |
     |   Federal Funds Rate target
     |
IORB                                     <-- Pavimento superiore
     |
SOFR                                     <-- Tipicamente appena sotto IORB
     |
ON RRP (Overnight Reverse Repo)          <-- Pavimento inferiore
```

### Perche' SOFR sta sotto IORB

In condizioni normali, il SOFR scambia **leggermente al di sotto dell'IORB** (tipicamente 1-10 punti base). La ragione e' strutturale:

1. **L'IORB e' accessibile solo alle banche** con conto alla Fed
2. Nel mercato repo operano anche soggetti **non bancari** (money market funds, GSE come Fannie Mae e Freddie Mac) che **non possono** depositare riserve alla Fed
3. Questi soggetti sono disposti a prestare a tassi leggermente inferiori all'IORB, perche' non hanno l'alternativa di depositare alla Fed
4. Le banche fanno **arbitraggio**: prendono in prestito nel mercato repo (a SOFR) e depositano alla Fed (a IORB), guadagnando lo spread
5. Questo arbitraggio tiene il SOFR vicino ma leggermente sotto l'IORB

### Quando lo spread si allarga

Lo spread SOFR-IORB puo' allargarsi temporaneamente in momenti di **stress nel mercato repo**:

- **Fine trimestre / fine anno**: le banche riducono la loro attivita' repo per ragioni di bilancio (window dressing), causando un'impennata del SOFR
- **Settembre 2019**: crisi del mercato repo dove il SOFR e' salito fino a ~5.25% (rispetto a un IOER del 2.10%), costringendo la Fed a intervenire con iniezioni di liquidita'
- **Scadenze fiscali**: flussi di cassa verso il Tesoro riducono la liquidita' disponibile

---

## Lettura del Grafico

### Pannello superiore: SOFR vs IORB

Il grafico mostra entrambi i tassi sovrapposti con dati giornalieri. Le osservazioni principali:

#### 2018-2019: Pre-COVID
- Entrambi i tassi seguono il ciclo di rialzo della Fed (dal ~1.7% al ~2.4%)
- Si nota lo **spike di settembre 2019** nel SOFR, quando il tasso e' schizzato brevemente sopra il 5% a causa di una crisi di liquidita' nel mercato repo
- La Fed ha iniziato a tagliare i tassi nella seconda meta' del 2019

#### 2020-2021: Era COVID
- La Fed ha tagliato i tassi a **0-0.25%** nel marzo 2020 in risposta alla pandemia
- Entrambi i tassi sono rimasti ancorati vicino allo zero per quasi due anni
- Liquidita' abbondante nel sistema grazie al QE massiccio

#### 2022-2023: Ciclo di rialzo aggressivo
- Il piu' rapido ciclo di rialzo dal 1980: da 0% a oltre 5.25% in meno di 18 mesi
- I "gradini" nel grafico corrispondono alle singole decisioni del FOMC
- SOFR e IORB si muovono in perfetto sincronismo, confermando l'efficacia del corridoio dei tassi

#### 2024-2025: Inizio del ciclo di taglio
- La Fed ha iniziato a tagliare i tassi nel settembre 2024
- Riduzione graduale, con i tassi che scendono verso il 4.25-4.50%
- Lo spread tra SOFR e IORB rimane stabile e contenuto

### Pannello inferiore: Spread SOFR - IORB

Il pannello inferiore mostra la differenza giornaliera tra SOFR e IORB:

- **Aree rosse** (spread negativo): SOFR < IORB — la condizione normale, che indica un mercato repo ben funzionante
- **Aree blu** (spread positivo): SOFR > IORB — segnale di stress o carenza di liquidita' nel mercato repo
- Lo spread si mantiene tipicamente tra **-0.05% e +0.05%** (5 punti base)
- Gli spike occasionali corrispondono a fine trimestre o eventi di mercato

---

## Implicazioni per gli Investitori

### Perche' questi tassi contano

1. **Costo opportunita'**: SOFR e IORB rappresentano il "risk-free rate" a breve termine. Qualsiasi investimento deve offrire un rendimento superiore per giustificare il rischio aggiuntivo.

2. **Valutazione degli asset**: tassi piu' alti significano che i flussi di cassa futuri valgono meno in termini attuali, il che deprime i prezzi di azioni e obbligazioni a lunga scadenza.

3. **Liquidita' di sistema**: quando lo spread SOFR-IORB si allarga, puo' essere un segnale precoce di stress nel sistema finanziario.

4. **Curva dei rendimenti**: SOFR e IORB ancorano l'estremita' corta della curva. Il confronto tra questi tassi e i rendimenti a lungo termine (es. Treasury 10Y) rivela le aspettative del mercato sull'economia.

### Relazione con il mercato obbligazionario

I tassi overnight come SOFR e IORB influenzano direttamente:
- I rendimenti dei **Treasury Bills** (scadenza < 1 anno)
- Il tasso dei **money market funds**
- I tassi sui **depositi bancari**
- Il costo di **finanziamento a margine** per i trader

Quando SOFR/IORB sono elevati (come nel 2023-2024 al 5%+), gli investitori hanno un forte incentivo a detenere strumenti a breve termine piuttosto che rischiare su obbligazioni a lunga scadenza o azioni — il cosiddetto effetto "cash is king".

---

## Fonti dei Dati

| Serie | Fonte | Codice FRED | Inizio serie |
|---|---|---|---|
| SOFR | Federal Reserve Bank of New York | `SOFR` | 3 aprile 2018 |
| IORB | Board of Governors of the Federal Reserve | `IORB` | 29 luglio 2021 |
| IOER (storico) | Board of Governors of the Federal Reserve | `IOER` | 9 ottobre 2008 |

I dati sono scaricati dalla piattaforma [FRED](https://fred.stlouisfed.org/) (Federal Reserve Economic Data) della Federal Reserve Bank of St. Louis, con frequenza giornaliera.

---

*Grafico e analisi generati ad aprile 2025. I dati sono soggetti a revisione da parte delle fonti ufficiali.*
