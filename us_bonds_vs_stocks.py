"""
US Stocks vs US Bonds — Rendimenti annui 1871–oggi  (100% runtime, zero dati hardcoded)
========================================================================================

Tutte le serie storiche vengono scaricate a runtime da tre fonti pubbliche e gratuite:

  1. Robert Shiller / Yale  (ie_data.xls)
     URL: http://www.econ.yale.edu/~shiller/data/ie_data.xls
     Copertura: 1871–oggi, mensile
     Fornisce: prezzi S&P Composite + dividendi + GS10 yield
     Uso: fonte base per 1910–1952 (bond) e 1910–1987 (stocks)

  2. FRED – Federal Reserve Bank of St. Louis  (GS10)
     URL: https://fred.stlouisfed.org/graph/fredgraph.csv?id=GS10
     Copertura: 1953–oggi, mensile
     Uso: sovrascrive i bond yield di Shiller con dati ufficiali Fed (più precisi)

  3. Yahoo Finance via yfinance  (^SP500TR, ^GSPC)
     Copertura: ^SP500TR 1988–oggi  |  ^GSPC 1927–oggi
     Uso: sovrascrive i rendimenti azionari con total return reali (dividendi inclusi)

Metodo di calcolo bond total return (duration model):
     ret_t ≈ yield_{t-1}  −  DURATION × (yield_t − yield_{t-1})
     con DURATION = 8.5 (approssima un 10yr Treasury par bond)

Dipendenze:
    pip install yfinance plotly pandas requests openpyxl numpy
    pip install "xlrd==1.2.0"   # per leggere .xls (Shiller) su Python 3.9
    pip install kaleido          # opzionale: export PNG/SVG
"""

import io
import warnings
from datetime import date

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import requests
import yfinance as yf

warnings.filterwarnings("ignore", category=FutureWarning)

# ── costanti ────────────────────────────────────────────────────────────────

BOND_DURATION   = 8.5
TODAY           = date.today()
START_YEAR      = 1919   # 1919 = inizio serie Moody's FRED (bond fallback)

SHILLER_URL     = "http://www.econ.yale.edu/~shiller/data/ie_data.xls"
FRED_GS10_URL   = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=GS10"
# Moody's Aaa mensile dal 1919: proxy bond yield pre-1953
# Serie per bond storici pre-1953: prova multipli ID FRED in ordine
FRED_HISTORICAL_BOND_IDS = [
    ("M1333AUSM193NNBR", "NBER Basic Yields LT Corp Bonds 1919+"),
    ("IRLTLT01USM156N",   "OECD LT Gov Bond Yield USA 1960+"),
    ("AAA",               "Moody Aaa Corporate 1983+"),
]


# ════════════════════════════════════════════════════════════════════════════
#  SORGENTE 1 — Shiller  (ie_data.xls)  — con diagnostica e fallback FRED Moody's
# ════════════════════════════════════════════════════════════════════════════

def _compute_shiller_series(df: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    """Calcola stocks/bonds annuali dal DataFrame grezzo di Shiller."""
    df.columns = [str(c).strip() for c in df.columns]

    col_map = {}
    for i, c in enumerate(df.columns):
        cl = c.lower().replace(" ", "").replace(".", "")
        if i == 0 or cl in ("date", "date1"):
            col_map[c] = "date_raw"
        elif cl == "p":
            col_map[c] = "price"
        elif cl == "d":
            col_map[c] = "dividend"
        elif "rate" in cl or "gs10" in cl or "long" in cl:
            col_map[c] = "gs10"

    if "gs10" not in col_map.values() and len(df.columns) > 6:
        col_map[df.columns[6]] = "gs10"

    df = df.rename(columns=col_map)
    df = df[["date_raw", "price", "dividend", "gs10"]].copy()
    df = df[pd.to_numeric(df["date_raw"], errors="coerce").notna()].copy()
    df["date_raw"] = df["date_raw"].astype(float)
    df["price"]    = pd.to_numeric(df["price"],    errors="coerce")
    df["dividend"] = pd.to_numeric(df["dividend"], errors="coerce")
    df["gs10"]     = pd.to_numeric(df["gs10"],     errors="coerce")
    df = df.dropna(subset=["date_raw", "price"])

    df["year"]  = df["date_raw"].astype(int)
    df["month"] = ((df["date_raw"] - df["year"]) * 100).round().astype(int)
    df["month"] = df["month"].replace(0, 1)
    df = df.sort_values(["year", "month"]).reset_index(drop=True)

    df["price_prev"]  = df["price"].shift(1)
    df["div_monthly"] = df["dividend"].fillna(0) / 12
    df["monthly_tr"]  = (df["price"] + df["div_monthly"]) / df["price_prev"] - 1
    df = df.dropna(subset=["monthly_tr"])

    annual_stocks = (
        df.groupby("year")["monthly_tr"]
          .apply(lambda x: (np.prod(1 + x) - 1) * 100)
          .round(2)
    )
    full_years    = df.groupby("year")["month"].count()
    full_years    = full_years[full_years == 12].index
    annual_stocks = annual_stocks[annual_stocks.index.isin(full_years)]

    dec_yield = df.groupby("year").apply(
        lambda g: g.loc[g["month"].idxmax(), "gs10"]
    ).dropna()

    bond_returns = {}
    years = sorted(dec_yield.index)
    for i in range(1, len(years)):
        y_prev, y_curr = dec_yield.iloc[i-1], dec_yield.iloc[i]
        bond_returns[years[i]] = round(y_prev - BOND_DURATION * (y_curr - y_prev), 2)

    return annual_stocks, pd.Series(bond_returns, name="bonds_shiller")


def fetch_shiller() -> tuple[pd.Series, pd.Series]:
    """
    Scarica ie_data.xls da Yale e lo legge con l'API NATIVA di xlrd 1.2.0,
    bypassando completamente pd.read_excel (che rifiuta xlrd < 2.0.1).

    xlrd.open_workbook() funziona direttamente con .xls OLE2 indipendentemente
    dalla versione di Pandas installata.
    """
    print("  Scarico Shiller ie_data.xls da Yale ...")
    resp = requests.get(SHILLER_URL, timeout=30)
    resp.raise_for_status()

    magic = resp.content[:4].hex()
    fmt   = "XLS (OLE2)" if magic == "d0cf11e0" else "XLSX (ZIP)" if magic == "504b0304" else f"sconosciuto ({magic})"
    print(f"  -> Formato rilevato: {fmt}  ({len(resp.content):,} bytes)")

    # ── Prova 1: xlrd native API (bypassa il version check di Pandas) ────────
    # pd.read_excel controlla che xlrd >= 2.0.1, ma xlrd 2.x non legge .xls OLE2.
    # Chiamando xlrd direttamente non c'e' nessun controllo versione.
    try:
        import xlrd as _xlrd
        wb = _xlrd.open_workbook(file_contents=resp.content)
        # Cerca il foglio "Data" (o il primo foglio disponibile)
        sheet_name = "Data" if "Data" in wb.sheet_names() else wb.sheet_names()[0]
        ws = wb.sheet_by_name(sheet_name)
        print(f"  -> xlrd native: foglio={sheet_name!r}, righe={ws.nrows}, colonne={ws.ncols}")

        # Riga 7 (0-indexed) = intestazioni, righe 8+ = dati
        HEADER_ROW = 7
        headers = [str(ws.cell_value(HEADER_ROW, c)).strip() for c in range(ws.ncols)]
        rows = [
            [ws.cell_value(r, c) for c in range(ws.ncols)]
            for r in range(HEADER_ROW + 1, ws.nrows)
        ]
        df = pd.DataFrame(rows, columns=headers)
        print(f"  -> DataFrame grezzo: {len(df)} righe x {len(df.columns)} colonne")
        return _compute_shiller_series(df)

    except ImportError:
        print("  [!] xlrd non installato. Esegui: python3 -m pip install \"xlrd==1.2.0\"")
    except Exception as e:
        print(f"  [!] xlrd native fallito: {type(e).__name__}: {e}")

    # ── Prova 2: openpyxl (funziona se il file è in realtà un xlsx rinominato) ─
    try:
        raw = io.BytesIO(resp.content)
        df = pd.read_excel(raw, sheet_name="Data", header=7, engine="openpyxl")
        print("  -> OK con openpyxl")
        return _compute_shiller_series(df)
    except Exception as e:
        print(f"  [!] openpyxl fallito: {type(e).__name__}: {e}")

    raise RuntimeError(
        "Impossibile leggere ie_data.xls.\n"
        "  Installa xlrd 1.2.0: python3 -m pip install \"xlrd==1.2.0\""
    )


# ════════════════════════════════════════════════════════════════════════════
#  SORGENTE 2 — FRED GS10  (sostituisce bond Shiller dal 1953 in poi)
# ════════════════════════════════════════════════════════════════════════════

def fetch_bonds_fred() -> pd.Series:
    """GS10 Treasury 10yr da FRED (mensile dal 1953) → total return annuo."""
    print("  Scarico FRED GS10 ...")
    return _fred_yield_to_annual_bond_returns(FRED_GS10_URL, "bonds_gs10")



# ════════════════════════════════════════════════════════════════════════════
#  SORGENTE 2b — FRED Moody's Aaa  (bond 1919–1952, fallback se Shiller fallisce)
# ════════════════════════════════════════════════════════════════════════════

def _fred_yield_to_annual_bond_returns(url: str, label: str) -> pd.Series:
    """
    Scarica un yield mensile da FRED e lo converte in rendimento annuo
    via duration model. Funzione generica usata sia per GS10 che per Moody's Aaa.
    """
    resp = requests.get(url, timeout=20)
    resp.raise_for_status()
    text = resp.text.lstrip("\ufeff")
    raw_df = pd.read_csv(io.StringIO(text))
    raw_df.columns = ["date_str", "yield_pct"]
    raw_df = raw_df[raw_df["yield_pct"] != "."].copy()
    raw_df["yield_pct"] = pd.to_numeric(raw_df["yield_pct"], errors="coerce")
    raw_df["date"]      = pd.to_datetime(raw_df["date_str"], errors="coerce")
    raw_df = raw_df.dropna(subset=["date", "yield_pct"])
    raw_df = raw_df.set_index("date").sort_index()

    try:
        annual_yield = raw_df["yield_pct"].resample("YE").last()
    except Exception:
        annual_yield = raw_df["yield_pct"].resample("A").last()
    annual_yield.index = annual_yield.index.year
    annual_yield = annual_yield.dropna()

    bond_returns = {}
    years = sorted(annual_yield.index)
    for i in range(1, len(years)):
        y_prev, y_curr = annual_yield.iloc[i-1], annual_yield.iloc[i]
        bond_returns[years[i]] = round(y_prev - BOND_DURATION * (y_curr - y_prev), 2)

    series = pd.Series(bond_returns, name=label)
    print(f"  -> {label}: {int(series.index.min())}–{int(series.index.max())}"
          f"  ({len(series)} anni)")
    return series


def fetch_bonds_aaa_historical() -> pd.Series:
    """
    Scarica yield obbligazionario storico pre-1953 da FRED.
    Prova una lista di series ID in ordine fino a trovarne uno valido.
    """
    print("  Scarico FRED bond storici pre-1953 ...")
    for series_id, label in FRED_HISTORICAL_BOND_IDS:
        url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
        try:
            result = _fred_yield_to_annual_bond_returns(url, f"bonds_hist({series_id})")
            if len(result) > 5:
                print(f"  -> Usata serie {series_id}: {label}")
                return result
        except Exception as e:
            print(f"  -> {series_id} non disponibile: {e}")
    raise RuntimeError("Nessuna serie FRED storica disponibile per i bond pre-1953.")


# ════════════════════════════════════════════════════════════════════════════
#  SORGENTE 3 — yfinance  (sostituisce stock Shiller dal 1927 in poi)
# ════════════════════════════════════════════════════════════════════════════

def _annual_returns(series: pd.Series) -> pd.Series:
    series = series.dropna()
    try:
        annual = series.resample("YE").last()
    except Exception:
        annual = series.resample("A").last()
    annual.index = annual.index.year
    return (annual.pct_change() * 100).dropna().round(2)


def fetch_stocks_yfinance() -> pd.Series:
    """
    Scarica ^SP500TR (total return 1988+) e ^GSPC (price return 1927+) da Yahoo.
    Combina i due: dove esiste il total return ha priorità.
    """
    end_str = str(TODAY)

    print("  Scarico ^SP500TR (total return, 1988–oggi) ...")
    raw_tr = yf.download("^SP500TR", start="1988-01-01", end=end_str,
                         auto_adjust=True, progress=False)
    # yfinance restituisce MultiIndex su columns → squeeze a Series 1D
    if isinstance(raw_tr.columns, pd.MultiIndex):
        spxtr = raw_tr["Close"].squeeze()
    else:
        spxtr = raw_tr["Close"] if "Close" in raw_tr.columns else raw_tr.iloc[:, 0]
    spxtr = spxtr.squeeze()

    print("  Scarico ^GSPC (price return, 1927–oggi) ...")
    raw_pr = yf.download("^GSPC", start="1927-01-01", end=end_str,
                         auto_adjust=True, progress=False)
    if isinstance(raw_pr.columns, pd.MultiIndex):
        gspc = raw_pr["Close"].squeeze()
    else:
        gspc = raw_pr["Close"] if "Close" in raw_pr.columns else raw_pr.iloc[:, 0]
    gspc = gspc.squeeze()

    ret_spxtr = _annual_returns(spxtr)
    ret_gspc  = _annual_returns(gspc)

    combined = ret_gspc.copy()
    combined.update(ret_spxtr)   # total return sovrascrive price return

    print(f"  -> yfinance stocks: {int(combined.index.min())}–{int(combined.index.max())}"
          f"  ({len(combined)} anni)")
    return combined


# ════════════════════════════════════════════════════════════════════════════
#  ASSEMBLY — merge delle tre sorgenti con ordine di priorità
# ════════════════════════════════════════════════════════════════════════════

def build_dataset() -> pd.DataFrame:
    """
    Costruisce il DataFrame finale fondendo le tre sorgenti.

    Priorità per STOCKS:
        Shiller  <  yfinance ^GSPC (1927+)  <  yfinance ^SP500TR (1988+)

    Priorità per BONDS:
        Shiller  <  FRED GS10 duration model (1953+)
    """
    print("\n=== FETCH DATI RUNTIME ===")

    # ── Shiller (opzionale: estende la copertura storica) ────────────────────
    try:
        stocks_shiller, bonds_shiller = fetch_shiller()
    except Exception as e:
        print(f"  [AVVISO] Shiller non disponibile: {e}")
        print("  Uso FRED Moody's Aaa come fallback per bond pre-1953.")
        stocks_shiller = pd.Series(dtype=float)
        bonds_shiller  = pd.Series(dtype=float)

    # ── FRED GS10 (bond 1954+) ────────────────────────────────────────────────
    try:
        bonds_fred = fetch_bonds_fred()
    except Exception as e:
        print(f"  [ERRORE] FRED GS10 non disponibile: {e}")
        bonds_fred = pd.Series(dtype=float)

    # ── FRED Moody's Aaa (bond 1919–1952, fallback se Shiller manca) ─────────
    try:
        bonds_aaa = fetch_bonds_aaa_historical()
    except Exception as e:
        print(f"  [ERRORE] FRED Moody's Aaa non disponibile: {e}")
        bonds_aaa = pd.Series(dtype=float)

    # ── yfinance (stocks 1928+) ───────────────────────────────────────────────
    try:
        stocks_yf = fetch_stocks_yfinance()
    except Exception as e:
        print(f"  [ERRORE] yfinance non disponibile: {e}")
        stocks_yf = pd.Series(dtype=float)

    # ── Diagnostica copertura ─────────────────────────────────────────────────
    print("\n  --- Copertura per fonte ---")
    def _rng(s):
        s = s.dropna()
        return f"{int(s.index.min())}–{int(s.index.max())}  ({len(s)} anni)" if len(s) else "VUOTA"
    print(f"  stocks_shiller : {_rng(stocks_shiller)}")
    print(f"  stocks_yf      : {_rng(stocks_yf)}")
    print(f"  bonds_shiller  : {_rng(bonds_shiller)}")
    print(f"  bonds_aaa_hist : {_rng(bonds_aaa)}")
    print(f"  bonds_gs10     : {_rng(bonds_fred)}")

    # ── Merge con ordine di priorità ──────────────────────────────────────────
    # Bonds: Moody's Aaa (1919+) < Shiller GS10 < FRED GS10 (1954+)
    # Stocks: Shiller Composite < yfinance GSPC (1928+) < yfinance SP500TR (1988+)
    all_years = list(range(START_YEAR, TODAY.year + 1))

    stocks_merged = stocks_shiller.reindex(all_years)
    stocks_merged.update(stocks_yf)

    bonds_merged = bonds_aaa.reindex(all_years)   # base: Moody's Aaa 1919+
    bonds_merged.update(bonds_shiller)             # sovrascrive con Shiller GS10
    bonds_merged.update(bonds_fred)                # sovrascrive con FRED GS10 (1954+)

    # ── Debug: quanti anni hanno entrambi i valori? ──────────────────────────
    tmp = pd.DataFrame({"stocks": stocks_merged, "bonds": bonds_merged})
    n_stocks_ok = tmp["stocks"].notna().sum()
    n_bonds_ok  = tmp["bonds"].notna().sum()
    n_both_ok   = tmp.dropna().shape[0]
    print(f"\n  --- Anni con dato valido ---")
    print(f"  stocks: {n_stocks_ok}  |  bonds: {n_bonds_ok}  |  entrambi: {n_both_ok}")
    if n_stocks_ok != n_bonds_ok:
        miss_s = tmp[tmp["stocks"].isna() & tmp["bonds"].notna()].index.tolist()
        miss_b = tmp[tmp["bonds"].isna()  & tmp["stocks"].notna()].index.tolist()
        if miss_s:
            print(f"  Anni con solo bonds (stocks mancante): {miss_s}")
        if miss_b:
            print(f"  Anni con solo stocks (bonds mancante): {miss_b}")

    df = tmp.dropna().reset_index()
    df.columns = ["year", "stocks", "bonds"]

    df["year"]       = df["year"].astype(int)
    df["decade"]     = (df["year"] // 10 * 10).astype(str) + "s"
    df["label"]      = df["year"].astype(str).str[-2:]
    df["is_partial"] = df["year"] == TODAY.year

    print(f"\n  DATASET FINALE: {len(df)} anni  ({df.year.min()}–{df.year.max()})")
    if df["is_partial"].any():
        ytd = df[df["is_partial"]].iloc[0]
        print(f"  Anno parziale {TODAY.year} YTD ({TODAY}): "
              f"Stocks {ytd.stocks:+.1f}%  |  Bonds {ytd.bonds:+.1f}%")

    return df


# ════════════════════════════════════════════════════════════════════════════
#  GRAFICO
# ════════════════════════════════════════════════════════════════════════════

DECADE_COLORS = {
    "1870s": "#aaaaaa", "1880s": "#cccccc", "1890s": "#999999",
    "1900s": "#dddddd",
    "1910s": "#ff9ff3",
    "1920s": "#f4d03f",
    "1930s": "#e74c3c",
    "1940s": "#e67e22",
    "1950s": "#2ecc71",
    "1960s": "#3498db",
    "1970s": "#9b59b6",
    "1980s": "#1abc9c",
    "1990s": "#e91e8c",
    "2000s": "#ff6b35",
    "2010s": "#00d4ff",
    "2020s": "#b8f55a",
}

NOTABLE = {
    1915: ("WW1 rally",     ( -30, -28)),
    1929: ("'29 Crash",     (  30,  28)),
    1931: ("'31 Crisi",     (  30,  28)),
    1933: ("'33 New Deal",  ( -30, -28)),
    1945: ("Fine WW2",      (  30, -28)),
    1974: ("Oil crisis",    (  30,  28)),
    1982: ("Volcker pivot", ( -30, -28)),
    2008: ("GFC",           ( -30,  28)),
    2022: ("Stagflazione",  ( -30,  28)),
}


def build_figure(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()

    x_min = max(-55, df.stocks.min() - 5)
    x_max = min(95,  df.stocks.max() + 5)
    y_min = max(-30, df.bonds.min() - 5)
    y_max = min(55,  df.bonds.max() + 5)

    for decade, group in df.groupby("decade", sort=True):
        color = DECADE_COLORS.get(decade, "#888888")

        hover_texts = []
        for row in group.itertuples():
            sc  = f"{'+'if row.stocks>=0 else ''}{row.stocks:.1f}%"
            bc  = f"{'+'if row.bonds>=0 else ''}{row.bonds:.1f}%"
            ytd = " <i>(YTD)</i>" if row.is_partial else ""
            hover_texts.append(
                f"<b>{row.year}{ytd}</b><br>"
                f"Stocks: <b>{sc}</b><br>"
                f"Bonds:  <b>{bc}</b>"
            )

        line_colors = [
            "#ffffff" if row.is_partial else "#0d1117"
            for row in group.itertuples()
        ]
        line_widths = [
            2.2 if row.is_partial else 0.8
            for row in group.itertuples()
        ]

        fig.add_trace(go.Scatter(
            x=group["stocks"],
            y=group["bonds"],
            mode="markers+text",
            name=decade,
            text=group["label"].tolist(),
            textposition="middle center",
            textfont=dict(family="'Courier New', monospace", size=7, color="#0d1117"),
            hovertext=hover_texts,
            hoverinfo="text",
            marker=dict(
                color=color, size=18, opacity=0.87,
                line=dict(color=line_colors, width=line_widths),
            ),
            legendgroup=decade,
        ))

    fig.add_vline(x=0, line=dict(color="#444c56", dash="dot", width=1))
    fig.add_hline(y=0, line=dict(color="#444c56", dash="dot", width=1))
    fig.add_shape(
        type="line",
        x0=min(x_min, y_min), y0=min(x_min, y_min),
        x1=max(x_max, y_max), y1=max(x_max, y_max),
        line=dict(color="#c9b037", dash="dash", width=1),
        opacity=0.28,
    )
    fig.add_annotation(
        x=25, y=28, text="stocks = bonds", showarrow=False,
        font=dict(color="#c9b037", size=9, family="monospace"),
        opacity=0.45, textangle=-20,
    )

    for year, (label, (ax, ay)) in NOTABLE.items():
        rows = df[df["year"] == year]
        if rows.empty:
            continue
        row = rows.iloc[0]
        fig.add_annotation(
            x=row.stocks, y=row.bonds, text=label, showarrow=True,
            arrowhead=2, arrowsize=0.8, arrowcolor="#8b949e", arrowwidth=1,
            ax=ax, ay=ay,
            font=dict(family="monospace", size=9, color="#c9d1d9"),
            bgcolor="#0d1117", bordercolor="#30363d",
            borderwidth=1, borderpad=3, opacity=0.9,
        )

    avg_s = df.stocks.mean()
    avg_b = df.bonds.mean()
    n_neg = len(df[(df.stocks < 0) & (df.bonds < 0)])

    fig.update_layout(
        title=dict(
            text=(
                f"<b>US Stocks vs US Bonds</b>  —  Rendimenti annui "
                f"{df.year.min()}–{df.year.max()}<br>"
                f"<sup>X = S&P 500 total return  |  Y = Bond 10yr (duration model)  |  "
                f"Media stocks {avg_s:+.1f}%  |  Media bonds {avg_b:+.1f}%  |  "
                f"Anni entrambi negativi: {n_neg}</sup>"
            ),
            font=dict(family="Georgia, serif", size=19, color="#f0f6fc"),
            x=0.5, xanchor="center",
        ),
        xaxis=dict(
            title=dict(text="Stock Return (%)",
                       font=dict(family="monospace", size=12, color="#8b949e")),
            range=[x_min, x_max], zeroline=False,
            gridcolor="#21262d",
            tickfont=dict(family="monospace", size=10, color="#8b949e"),
            ticksuffix="%",
        ),
        yaxis=dict(
            title=dict(text="Bond Return (%)",
                       font=dict(family="monospace", size=12, color="#8b949e")),
            range=[y_min, y_max], zeroline=False,
            gridcolor="#21262d",
            tickfont=dict(family="monospace", size=10, color="#8b949e"),
            ticksuffix="%",
        ),
        plot_bgcolor="#161b22",
        paper_bgcolor="#0d1117",
        legend=dict(
            title=dict(text="Decade", font=dict(color="#8b949e", size=11)),
            font=dict(family="monospace", size=11, color="#e6edf3"),
            bgcolor="#161b22", bordercolor="#30363d", borderwidth=1,
            itemclick="toggle", itemdoubleclick="toggleothers",
        ),
        hoverlabel=dict(
            bgcolor="#0d1117", bordercolor="#30363d",
            font=dict(family="monospace", size=12, color="#e6edf3"),
        ),
        width=1200, height=720,
        margin=dict(t=110, b=70, l=70, r=40),
    )

    fig.add_annotation(
        xref="paper", yref="paper", x=0, y=-0.09,
        text=(
            "Fonti: Shiller/Yale ie_data.xls (base storica 1871+)  ·  "
            "FRED GS10 duration model 8.5yr (sovrascrive bond 1953+)  ·  "
            "yfinance ^SP500TR / ^GSPC (sovrascrive stocks 1927+)  ·  "
            f"Generato il {TODAY}"
        ),
        showarrow=False,
        font=dict(size=9, color="#484f58", family="monospace"),
        align="left",
    )

    return fig


# ════════════════════════════════════════════════════════════════════════════
#  MAIN
# ════════════════════════════════════════════════════════════════════════════

def main():
    df = build_dataset()

    print("\n=== STATISTICHE ===")
    print(f"{'Anni totali:':<32} {len(df)}")
    print(f"{'Media Stocks:':<32} {df.stocks.mean():+.2f}%")
    print(f"{'Media Bonds:':<32} {df.bonds.mean():+.2f}%")
    best  = df.loc[df.stocks.idxmax()]
    worst = df.loc[df.stocks.idxmin()]
    print(f"{'Miglior anno Stocks:':<32} {int(best.year)} ({best.stocks:+.1f}%)")
    print(f"{'Peggior anno Stocks:':<32} {int(worst.year)} ({worst.stocks:+.1f}%)")
    neg = df[(df.stocks < 0) & (df.bonds < 0)]
    print(f"{'Anni entrambi negativi:':<32} {len(neg)}")
    print(f"  -> {', '.join(neg.year.astype(str).tolist())}")
    print("=" * 45)

    fig = build_figure(df)

    fig.show()

    out = "us_bonds_vs_stocks.html"
    fig.write_html(out, include_plotlyjs="cdn")
    print(f"\nSalvato: {out}")

    # PNG ad alta risoluzione (richiede: pip install kaleido)
    # fig.write_image("us_bonds_vs_stocks.png", scale=2)


if __name__ == "__main__":
    main()