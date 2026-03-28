"""
US Stocks vs US Bonds — genera DUE file HTML a runtime
=======================================================

HTML 1 — "runtime_gs10.html"
    Stocks : ^GSPC price return (1927+)  sovrascritta da ^SP500TR total return (1988+)
    Bonds  : FRED GS10 (10yr Treasury) + duration model 8.5yr
    Parte da: 1919 (Moody's Aaa FRED come bond pre-1953)

HTML 2 — "runtime_ibbotson.html"   ← logica equivalente al JSX hardcoded
    Stocks : Shiller total return composto (dividendi inclusi, 1872+)
             sovrascritta da ^SP500TR total return (1988+)
    Bonds  : Shiller GS10 yield + duration model 14yr (proxy LT Gov 20-30yr)
             sovrascritta da FRED GS30 30yr Treasury + duration 14yr (1977+)
    Parte da: 1910

Fonti:
    Shiller/Yale  : http://www.econ.yale.edu/~shiller/data/ie_data.xls
    FRED GS10     : https://fred.stlouisfed.org/graph/fredgraph.csv?id=GS10
    FRED GS30     : https://fred.stlouisfed.org/graph/fredgraph.csv?id=GS30
    FRED Moody's  : https://fred.stlouisfed.org/graph/fredgraph.csv?id=AAA
    yfinance      : ^SP500TR (1988+), ^GSPC (1927+)

Dipendenze:
    pip install yfinance plotly pandas requests "xlrd==1.2.0" openpyxl numpy
"""

import base64, io, re, struct, warnings
from datetime import date

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import requests
import yfinance as yf

warnings.filterwarnings("ignore", category=FutureWarning)

# ── costanti ─────────────────────────────────────────────────────────────────
TODAY         = date.today()
DURATION_GS10 = 8.5    # duration modificata Treasury 10yr
DURATION_LT   = 14.0   # duration modificata LT Gov Bond 20-30yr (stile Ibbotson)

SHILLER_URL   = "http://www.econ.yale.edu/~shiller/data/ie_data.xls"
FRED_GS10_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=GS10"
FRED_GS30_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=GS30"
FRED_AAA_URL  = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=AAA"


# ════════════════════════════════════════════════════════════════════════════
#  FETCH — Shiller ie_data.xls  (lettura nativa xlrd, bypassa pd.read_excel)
# ════════════════════════════════════════════════════════════════════════════

def fetch_shiller() -> dict:
    """
    Legge ie_data.xls con l'API NATIVA di xlrd (bypassa il version-check di Pandas).
    Restituisce un dict con:
        'stocks_tr'  : rendimento annuo S&P Composite total return (%)
        'bond_yield' : yield GS10 di fine anno (%), usato per duration model
    """
    print("  [Shiller] Scarico ie_data.xls ...")
    resp = requests.get(SHILLER_URL, timeout=30)
    resp.raise_for_status()

    magic = resp.content[:4].hex()
    is_xls = (magic == "d0cf11e0")
    print(f"  [Shiller] Formato: {'XLS OLE2' if is_xls else 'altro (' + magic + ')'}  "
          f"({len(resp.content):,} bytes)")

    df = None

    # --- Prova 1: xlrd native (bypassa pandas version check) ---
    if is_xls:
        try:
            import xlrd as _xlrd
            wb = _xlrd.open_workbook(file_contents=resp.content)
            sheet_name = "Data" if "Data" in wb.sheet_names() else wb.sheet_names()[0]
            ws = wb.sheet_by_name(sheet_name)
            # Riga 7 (0-indexed) = intestazioni
            headers = [str(ws.cell_value(7, c)).strip() for c in range(ws.ncols)]
            rows    = [[ws.cell_value(r, c) for c in range(ws.ncols)]
                       for r in range(8, ws.nrows)]
            df = pd.DataFrame(rows, columns=headers)
            print(f"  [Shiller] xlrd native OK — {len(df)} righe, colonne: {list(df.columns[:8])}")
        except ImportError:
            print("  [Shiller] xlrd non installato: python3 -m pip install \"xlrd==1.2.0\"")
        except Exception as e:
            print(f"  [Shiller] xlrd native fallito: {e}")

    # --- Prova 2: openpyxl (se il file fosse in realtà xlsx) ---
    if df is None:
        try:
            df = pd.read_excel(io.BytesIO(resp.content),
                               sheet_name="Data", header=7, engine="openpyxl")
            print(f"  [Shiller] openpyxl OK — {len(df)} righe")
        except Exception as e:
            print(f"  [Shiller] openpyxl fallito: {e}")

    if df is None:
        raise RuntimeError("Impossibile leggere ie_data.xls — vedi errori sopra.")

    # ── normalizza colonne ────────────────────────────────────────────────────
    df.columns = [str(c).strip() for c in df.columns]
    col_map = {}
    for i, c in enumerate(df.columns):
        cl = c.lower().replace(" ", "").replace(".", "")
        if i == 0 or cl in ("date", "date1"):       col_map[c] = "date_raw"
        elif cl == "p":                               col_map[c] = "price"
        elif cl == "d":                               col_map[c] = "dividend"
        elif "rate" in cl or "gs10" in cl or "long" in cl: col_map[c] = "gs10"
    if "gs10" not in col_map.values() and len(df.columns) > 6:
        col_map[df.columns[6]] = "gs10"
    df = df.rename(columns=col_map)

    df = df[["date_raw", "price", "dividend", "gs10"]].copy()
    df = df[pd.to_numeric(df["date_raw"], errors="coerce").notna()].copy()
    for col in ("date_raw", "price", "dividend", "gs10"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["date_raw", "price"])

    df["year"]  = df["date_raw"].astype(int)
    df["month"] = ((df["date_raw"] - df["year"]) * 100).round().astype(int)
    df["month"] = df["month"].replace(0, 1)
    df = df.sort_values(["year", "month"]).reset_index(drop=True)

    # ── total return mensile: (P_t + D_t/12) / P_{t-1} - 1 ──────────────────
    df["price_prev"]  = df["price"].shift(1)
    df["div_monthly"] = df["dividend"].fillna(0) / 12
    df["monthly_tr"]  = (df["price"] + df["div_monthly"]) / df["price_prev"] - 1
    df = df.dropna(subset=["monthly_tr"])

    # rendimento annuo: prodotto composto 12 mesi
    annual_tr = (
        df.groupby("year")["monthly_tr"]
          .apply(lambda x: (np.prod(1 + x) - 1) * 100)
          .round(2)
    )
    full_years = df.groupby("year")["month"].count()
    full_years = full_years[full_years == 12].index
    annual_tr  = annual_tr[annual_tr.index.isin(full_years)]

    # yield GS10 di fine anno (per duration model bonds)
    dec_yield = df.groupby("year").apply(
        lambda g: g.loc[g["month"].idxmax(), "gs10"]
    ).dropna()

    print(f"  [Shiller] stocks TR: {int(annual_tr.index.min())}–{int(annual_tr.index.max())}"
          f"  ({len(annual_tr)} anni)")
    print(f"  [Shiller] GS10 yield: {int(dec_yield.index.min())}–{int(dec_yield.index.max())}"
          f"  ({len(dec_yield)} anni)")

    return {"stocks_tr": annual_tr, "bond_yield": dec_yield}


# ════════════════════════════════════════════════════════════════════════════
#  FETCH — FRED (yield mensile → total return via duration model)
# ════════════════════════════════════════════════════════════════════════════

def _fred_yield_series(url: str, label: str) -> pd.Series:
    """Scarica un yield mensile da FRED, ritorna Series con index=anno, value=yield fine anno."""
    resp = requests.get(url, timeout=20)
    resp.raise_for_status()
    text = resp.text.lstrip("\ufeff")
    raw  = pd.read_csv(io.StringIO(text))
    raw.columns = ["date_str", "yield_pct"]
    raw = raw[raw["yield_pct"] != "."].copy()
    raw["yield_pct"] = pd.to_numeric(raw["yield_pct"], errors="coerce")
    raw["date"]      = pd.to_datetime(raw["date_str"], errors="coerce")
    raw = raw.dropna(subset=["date", "yield_pct"]).set_index("date").sort_index()
    try:
        annual = raw["yield_pct"].resample("YE").last()
    except Exception:
        annual = raw["yield_pct"].resample("A").last()
    annual.index = annual.index.year
    annual = annual.dropna()
    print(f"  [FRED {label}] {int(annual.index.min())}–{int(annual.index.max())}"
          f"  ({len(annual)} anni)")
    return annual


def yield_to_bond_returns(yield_series: pd.Series, duration: float) -> pd.Series:
    """Converte una serie di yield annuali in total return via duration model."""
    years   = sorted(yield_series.index)
    returns = {}
    for i in range(1, len(years)):
        y_prev = yield_series.iloc[i - 1]
        y_curr = yield_series.iloc[i]
        returns[years[i]] = round(y_prev - duration * (y_curr - y_prev), 2)
    return pd.Series(returns)


# ════════════════════════════════════════════════════════════════════════════
#  FETCH — yfinance
# ════════════════════════════════════════════════════════════════════════════

def _annual_returns_from_prices(series: pd.Series) -> pd.Series:
    series = series.squeeze().dropna()
    if isinstance(series, pd.DataFrame):
        series = series.iloc[:, 0]
    try:
        annual = series.resample("YE").last()
    except Exception:
        annual = series.resample("A").last()
    annual.index = annual.index.year
    return (annual.pct_change() * 100).dropna().round(2)


def fetch_yfinance() -> dict:
    """Scarica ^SP500TR (total return 1988+) e ^GSPC (price return 1927+)."""
    end = str(TODAY)

    print("  [yfinance] Scarico ^SP500TR ...")
    raw_tr = yf.download("^SP500TR", start="1988-01-01", end=end,
                         auto_adjust=True, progress=False)
    col_tr = raw_tr["Close"] if not isinstance(raw_tr.columns, pd.MultiIndex) \
             else raw_tr["Close"].squeeze()
    ret_tr = _annual_returns_from_prices(col_tr)

    print("  [yfinance] Scarico ^GSPC ...")
    raw_pr = yf.download("^GSPC", start="1927-01-01", end=end,
                         auto_adjust=True, progress=False)
    col_pr = raw_pr["Close"] if not isinstance(raw_pr.columns, pd.MultiIndex) \
             else raw_pr["Close"].squeeze()
    ret_pr = _annual_returns_from_prices(col_pr)

    # combina: price return come base, total return sovrascrive dal 1988
    combined = ret_pr.copy()
    combined.update(ret_tr)

    print(f"  [yfinance] stocks combinati: {int(combined.index.min())}–{int(combined.index.max())}")
    return {"stocks_price_then_tr": combined, "stocks_tr_only": ret_tr}


# ════════════════════════════════════════════════════════════════════════════
#  BUILD DATASETS
# ════════════════════════════════════════════════════════════════════════════

def build_datasets() -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Ritorna (df_gs10, df_ibbotson).

    df_gs10      : metodologia "runtime" — GSPC price→TR + GS10 duration 8.5
    df_ibbotson  : metodologia "Ibbotson" — Shiller TR + LT bond duration 14
    """
    print("\n" + "="*60)
    print("  FETCH DATI RUNTIME")
    print("="*60)

    # ── Shiller ──────────────────────────────────────────────────────────────
    shiller = None
    try:
        shiller = fetch_shiller()
    except Exception as e:
        print(f"  [AVVISO] Shiller non disponibile: {e}")

    # ── FRED GS10 ─────────────────────────────────────────────────────────────
    gs10_yield = None
    try:
        print("  [FRED] Scarico GS10 ...")
        gs10_yield = _fred_yield_series(FRED_GS10_URL, "GS10")
    except Exception as e:
        print(f"  [ERRORE] FRED GS10: {e}")

    # ── FRED GS30 (per metodologia Ibbotson) ─────────────────────────────────
    gs30_yield = None
    try:
        print("  [FRED] Scarico GS30 ...")
        gs30_yield = _fred_yield_series(FRED_GS30_URL, "GS30")
    except Exception as e:
        print(f"  [ERRORE] FRED GS30: {e}")

    # ── FRED Moody's AAA (fallback bond pre-1953 per df_gs10) ─────────────────
    aaa_yield = None
    try:
        print("  [FRED] Scarico Moody's AAA ...")
        aaa_yield = _fred_yield_series(FRED_AAA_URL, "AAA")
    except Exception as e:
        print(f"  [ERRORE] FRED AAA: {e}")

    # ── yfinance ──────────────────────────────────────────────────────────────
    yf_data = None
    try:
        yf_data = fetch_yfinance()
    except Exception as e:
        print(f"  [ERRORE] yfinance: {e}")

    # ════════════════════════════════════════════════════════════════════════
    #  DATASET 1 — GS10  (metodologia "runtime", come l'HTML corrente)
    #  Stocks : GSPC price return → SP500TR total return 1988+
    #  Bonds  : Moody's AAA (base pre-1953) → GS10 duration 8.5 (1954+)
    # ════════════════════════════════════════════════════════════════════════
    all_years_1 = list(range(1919, TODAY.year + 1))

    # bonds
    b1 = pd.Series(dtype=float)
    if aaa_yield is not None:
        b1_base = yield_to_bond_returns(aaa_yield, DURATION_GS10)
        b1 = b1_base.reindex(all_years_1)
    if gs10_yield is not None:
        b1_gs10 = yield_to_bond_returns(gs10_yield, DURATION_GS10)
        b1.update(b1_gs10)

    # stocks
    s1 = pd.Series(dtype=float)
    if yf_data is not None:
        s1 = yf_data["stocks_price_then_tr"].reindex(all_years_1)

    df1 = pd.DataFrame({"year": all_years_1,
                         "stocks": s1.values,
                         "bonds":  b1.values}).dropna()
    df1["year"] = df1["year"].astype(int)
    df1["is_partial"] = df1["year"] == TODAY.year

    # ════════════════════════════════════════════════════════════════════════
    #  DATASET 2 — Ibbotson  (metodologia equivalente al JSX)
    #  Stocks : Shiller TR composto (1872+) → SP500TR 1988+
    #  Bonds  : Shiller GS10 yield duration 14 → GS30 duration 14 (1977+)
    # ════════════════════════════════════════════════════════════════════════
    all_years_2 = list(range(1910, TODAY.year + 1))

    # stocks
    s2 = pd.Series(dtype=float, index=all_years_2)
    if shiller is not None:
        s2.update(shiller["stocks_tr"].reindex(all_years_2))
    if yf_data is not None:
        s2.update(yf_data["stocks_tr_only"])   # SP500TR sovrascrive dal 1988

    # bonds: yield di base da Shiller, poi aggiornato con GS30 dal 1977
    yield_base = pd.Series(dtype=float)
    if shiller is not None:
        yield_base = shiller["bond_yield"]
    if gs30_yield is not None:
        yield_base = yield_base.copy()
        # update sovrascrive ma non aggiunge chiavi nuove → concat prima
        new_keys = gs30_yield[~gs30_yield.index.isin(yield_base.index)]
        yield_base = pd.concat([yield_base, new_keys])
        yield_base.update(gs30_yield)

    b2 = yield_to_bond_returns(yield_base, DURATION_LT).reindex(all_years_2)

    df2 = pd.DataFrame({"year": all_years_2,
                         "stocks": s2.values,
                         "bonds":  b2.values}).dropna()
    df2["year"] = df2["year"].astype(int)
    df2["is_partial"] = df2["year"] == TODAY.year

    print(f"\n  Dataset GS10      : {len(df1)} anni  ({df1.year.min()}–{df1.year.max()})")
    print(f"  Dataset Ibbotson  : {len(df2)} anni  ({df2.year.min()}–{df2.year.max()})")

    return df1, df2


# ════════════════════════════════════════════════════════════════════════════
#  GRAFICO
# ════════════════════════════════════════════════════════════════════════════

DECADE_COLORS = {
    "1870s": "#888888", "1880s": "#aaaaaa", "1890s": "#bbbbbb", "1900s": "#cccccc",
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
    1929: ("'29 Crash",     ( 30,  28)),
    1931: ("'31 Crisi",     ( 30,  28)),
    1933: ("'33 New Deal",  (-30, -28)),
    1945: ("Fine WW2",      ( 30, -28)),
    1974: ("Oil crisis",    ( 30,  28)),
    1982: ("Volcker pivot", (-30, -28)),
    2008: ("GFC",           (-30,  28)),
    2022: ("Stagflazione",  (-30,  28)),
}


def build_figure(df: pd.DataFrame, title: str, subtitle: str, source_note: str) -> go.Figure:
    fig = go.Figure()

    stocks_range = [min(-55, df.stocks.min() - 5), max(90, df.stocks.max() + 5)]
    bonds_range  = [min(-30, df.bonds.min()  - 5), max(50, df.bonds.max()  + 5)]

    df["decade"] = (df["year"] // 10 * 10).astype(str) + "s"
    df["label"]  = df["year"].astype(str).str[-2:]

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

        line_colors = ["#ffffff" if r.is_partial else "#0d1117" for r in group.itertuples()]
        line_widths = [2.2      if r.is_partial else 0.8       for r in group.itertuples()]

        fig.add_trace(go.Scatter(
            x=group["stocks"], y=group["bonds"],
            mode="markers+text",
            name=decade,
            text=group["label"].tolist(),
            textposition="middle center",
            textfont=dict(family="'Courier New', monospace", size=7, color="#0d1117"),
            hovertext=hover_texts, hoverinfo="text",
            marker=dict(color=color, size=18, opacity=0.87,
                        line=dict(color=line_colors, width=line_widths)),
            legendgroup=decade,
        ))

    fig.add_vline(x=0, line=dict(color="#444c56", dash="dot", width=1))
    fig.add_hline(y=0, line=dict(color="#444c56", dash="dot", width=1))

    diag_min = min(stocks_range[0], bonds_range[0])
    diag_max = max(stocks_range[1], bonds_range[1])
    fig.add_shape(type="line",
                  x0=diag_min, y0=diag_min, x1=diag_max, y1=diag_max,
                  line=dict(color="#c9b037", dash="dash", width=1), opacity=0.28)
    fig.add_annotation(x=25, y=28, text="stocks = bonds", showarrow=False,
                       font=dict(color="#c9b037", size=9, family="monospace"),
                       opacity=0.45, textangle=-20)

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
            bgcolor="#0d1117", bordercolor="#30363d", borderwidth=1, borderpad=3, opacity=0.9,
        )

    avg_s = df.stocks.mean()
    avg_b = df.bonds.mean()
    n_neg = len(df[(df.stocks < 0) & (df.bonds < 0)])

    fig.update_layout(
        title=dict(
            text=(
                f"<b>{title}</b>  —  {df.year.min()}–{df.year.max()}<br>"
                f"<sup>{subtitle}  |  "
                f"Media stocks {avg_s:+.1f}%  |  Media bonds {avg_b:+.1f}%  |  "
                f"Anni entrambi negativi: {n_neg}</sup>"
            ),
            font=dict(family="Georgia, serif", size=19, color="#f0f6fc"),
            x=0.5, xanchor="center",
        ),
        xaxis=dict(
            title=dict(text="Stock Return (%)",
                       font=dict(family="monospace", size=12, color="#8b949e")),
            range=stocks_range, zeroline=False, gridcolor="#21262d",
            tickfont=dict(family="monospace", size=10, color="#8b949e"), ticksuffix="%",
        ),
        yaxis=dict(
            title=dict(text="Bond Return (%)",
                       font=dict(family="monospace", size=12, color="#8b949e")),
            range=bonds_range, zeroline=False, gridcolor="#21262d",
            tickfont=dict(family="monospace", size=10, color="#8b949e"), ticksuffix="%",
        ),
        plot_bgcolor="#161b22", paper_bgcolor="#0d1117",
        legend=dict(
            title=dict(text="Decade", font=dict(color="#8b949e", size=11)),
            font=dict(family="monospace", size=11, color="#e6edf3"),
            bgcolor="#161b22", bordercolor="#30363d", borderwidth=1,
            itemclick="toggle", itemdoubleclick="toggleothers",
        ),
        hoverlabel=dict(bgcolor="#0d1117", bordercolor="#30363d",
                        font=dict(family="monospace", size=12, color="#e6edf3")),
        autosize=True,
        margin=dict(t=110, b=80, l=70, r=40),
    )

    fig.add_annotation(
        xref="paper", yref="paper", x=0, y=-0.10,
        text=f"{source_note}  ·  Generato il {TODAY}",
        showarrow=False,
        font=dict(size=9, color="#484f58", family="monospace"), align="left",
    )

    return fig


# ════════════════════════════════════════════════════════════════════════════
#  FULLSCREEN HTML
# ════════════════════════════════════════════════════════════════════════════

_FULLSCREEN_HEAD = (
    '<head><meta charset="utf-8" />'
    '<meta name="viewport" content="width=device-width, initial-scale=1" />'
    '<style>'
    'html,body{margin:0;padding:0;height:100%;width:100%;overflow:hidden}'
    '.plotly-graph-div{width:100vw!important;height:100vh!important}'
    '</style></head>'
)

def _inject_fullscreen_css(path: str):
    html = open(path, encoding="utf-8").read()
    html = html.replace('<head><meta charset="utf-8" /></head>', _FULLSCREEN_HEAD)
    open(path, "w", encoding="utf-8").write(html)


# ════════════════════════════════════════════════════════════════════════════
#  MAIN
# ════════════════════════════════════════════════════════════════════════════

def print_stats(df: pd.DataFrame, label: str):
    print(f"\n  [{label}]")
    print(f"    Anni: {len(df)}  ({df.year.min()}–{df.year.max()})")
    print(f"    Media stocks: {df.stocks.mean():+.2f}%  |  Media bonds: {df.bonds.mean():+.2f}%")
    best  = df.loc[df.stocks.idxmax()]
    worst = df.loc[df.stocks.idxmin()]
    print(f"    Miglior anno stocks: {int(best.year)} ({best.stocks:+.1f}%)")
    print(f"    Peggior anno stocks: {int(worst.year)} ({worst.stocks:+.1f}%)")
    neg = df[(df.stocks < 0) & (df.bonds < 0)]
    print(f"    Anni entrambi negativi: {len(neg)} — {list(neg.year.astype(int))}")


def main():
    df_gs10, df_ibbotson = build_datasets()

    print("\n" + "="*60)
    print("  STATISTICHE")
    print("="*60)
    print_stats(df_gs10,     "GS10 / GSPC price→TR")
    print_stats(df_ibbotson, "Ibbotson / Shiller TR + LT Bond dur.14")

    # ── HTML 1: GS10 metodologia ──────────────────────────────────────────────
    fig1 = build_figure(
        df_gs10,
        title    = "US Stocks vs US Bonds",
        subtitle = "X = S&P 500 (price→TR dal 1988)  |  Y = Bond 10yr GS10 duration 8.5",
        source_note = "Stocks: yfinance ^GSPC / ^SP500TR  ·  Bonds: FRED GS10 + Moody's AAA duration 8.5yr",
    )
    out1 = "runtime_gs10.html"
    fig1.write_html(out1, include_plotlyjs="cdn")
    _inject_fullscreen_css(out1)
    print(f"\n  Salvato: {out1}")

    # ── HTML 2: Ibbotson metodologia ──────────────────────────────────────────
    fig2 = build_figure(
        df_ibbotson,
        title    = "US Stocks vs US Bonds  [Metodologia Ibbotson]",
        subtitle = "X = S&P 500 total return (Shiller + SP500TR)  |  Y = LT Gov Bond GS30 duration 14",
        source_note = "Stocks: Shiller ie_data.xls TR composto / ^SP500TR  ·  Bonds: Shiller GS10 + FRED GS30 duration 14yr",
    )
    out2 = "runtime_ibbotson.html"
    fig2.write_html(out2, include_plotlyjs="cdn")
    _inject_fullscreen_css(out2)
    print(f"  Salvato: {out2}")


if __name__ == "__main__":
    main()