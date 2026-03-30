"""
US Stocks vs US Bonds — Analisi ML e Pattern
=============================================

Genera un singolo file HTML interattivo (analysis.html) con 6 analisi:
  1. Market Regime Clustering (GMM)
  2. Matrice di Transizione Markov
  3. Correlazione Rolling Azioni-Bond
  4. CAPE come Predittore dei Rendimenti Futuri
  5. Mean Reversion / Rendimenti Condizionali
  6. Autocorrelazione e Cicli

Dipendenze:
    pip install -r requirements.txt
"""

import io, warnings
from datetime import date

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
from scipy import signal
from sklearn.mixture import GaussianMixture

from us_bonds_vs_stocks import (
    build_datasets, SHILLER_URL, DECADE_COLORS,
)

warnings.filterwarnings("ignore", category=FutureWarning)

TODAY = date.today()

# ── tema scuro coerente con i grafici esistenti ──────────────────────────────
PAPER_BG  = "#0d1117"
PLOT_BG   = "#161b22"
GRID_COL  = "#21262d"
TEXT_COL  = "#e6edf3"
MUTED_COL = "#8b949e"
FONT_MONO = "'Source Code Pro', 'Fira Code', Consolas, monospace"
FONT_TEXT = "'Inter', 'Segoe UI', 'Helvetica Neue', sans-serif"

REGIME_COLORS = {
    "Goldilocks":            "#3fb950",  # verde
    "Fuga verso la qualità": "#58a6ff",  # blu
    "Boom con tassi in salita": "#d29922", # oro
    "Stagflazione / Crisi":  "#f85149",  # rosso
}

QUADRANT_NAMES = ["Azioni+ Bond+", "Azioni- Bond+", "Azioni- Bond-", "Azioni+ Bond-"]
QUADRANT_COLORS = ["#3fb950", "#58a6ff", "#f85149", "#d29922"]


# ════════════════════════════════════════════════════════════════════════════
#  FETCH SHILLER ESTESO — estrae anche CAPE e CPI
# ════════════════════════════════════════════════════════════════════════════

def fetch_shiller_extended() -> pd.DataFrame:
    """
    Legge ie_data.xls e restituisce un DataFrame annuale con:
    year, price, gs10, cpi, cape
    """
    print("  [Shiller Extended] Scarico ie_data.xls ...")
    resp = requests.get(SHILLER_URL, timeout=30)
    resp.raise_for_status()

    import xlrd as _xlrd
    wb = _xlrd.open_workbook(file_contents=resp.content)
    sheet_name = "Data" if "Data" in wb.sheet_names() else wb.sheet_names()[0]
    ws = wb.sheet_by_name(sheet_name)
    headers = [str(ws.cell_value(7, c)).strip() for c in range(ws.ncols)]
    rows = [[ws.cell_value(r, c) for c in range(ws.ncols)]
            for r in range(8, ws.nrows)]
    df = pd.DataFrame(rows, columns=headers)

    # ── normalizza colonne ────────────────────────────────────────────────
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
            if "gs10" not in col_map.values():
                col_map[c] = "gs10"
        elif cl == "cpi" and "cpi" not in col_map.values():
            col_map[c] = "cpi"
        elif (cl == "cape" or cl == "pe10" or cl == "p/e10") and "cape" not in col_map.values():
            col_map[c] = "cape"
        elif cl == "e" and "earnings" not in col_map.values():
            col_map[c] = "earnings"

    df = df.rename(columns=col_map)

    keep = [c for c in ["date_raw", "price", "dividend", "gs10", "cpi", "cape"]
            if c in df.columns]
    df = df[keep].copy()
    # rimuovi colonne duplicate (es. due colonne "cape")
    df = df.loc[:, ~df.columns.duplicated()]
    df = df[pd.to_numeric(df["date_raw"], errors="coerce").notna()].copy()
    for col in keep:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df["year"] = df["date_raw"].astype(int)
    df["month"] = ((df["date_raw"] - df["year"]) * 100).round().astype(int)
    df["month"] = df["month"].replace(0, 1)
    df = df.sort_values(["year", "month"]).reset_index(drop=True)

    # valore annuale = ultimo mese disponibile per ogni anno
    idx = df.groupby("year")["month"].idxmax()
    annual = df.loc[idx].reset_index(drop=True)

    # CPI → inflazione annua
    annual = annual.sort_values("year").reset_index(drop=True)
    if "cpi" in annual.columns:
        annual["inflation"] = annual["cpi"].pct_change() * 100

    result = annual[["year"] + [c for c in ["price", "cape", "cpi", "inflation"]
                                if c in annual.columns]].copy()
    result["year"] = result["year"].astype(int)

    print(f"  [Shiller Extended] {int(result.year.min())}–{int(result.year.max())}"
          f"  colonne: {list(result.columns)}")
    return result


# ════════════════════════════════════════════════════════════════════════════
#  ANALISI 1 — Market Regime Clustering (GMM)
# ════════════════════════════════════════════════════════════════════════════

def analysis_regime_clustering(df: pd.DataFrame) -> tuple:
    X = df[["stocks", "bonds"]].values

    # BIC per scegliere n_components
    bics = []
    for n in range(2, 7):
        gmm = GaussianMixture(n_components=n, covariance_type="full",
                               n_init=10, random_state=42)
        gmm.fit(X)
        bics.append((n, gmm.bic(X)))
    best_n = min(bics, key=lambda x: x[1])[0]
    print(f"  [GMM] BIC ottimale: {best_n} componenti")

    # fit con 4 componenti (scelta interpretativa: 4 quadranti economici)
    n_clusters = 4
    gmm = GaussianMixture(n_components=n_clusters, covariance_type="full",
                           n_init=20, random_state=42)
    gmm.fit(X)
    labels = gmm.predict(X)

    # assegna nomi intuitivi in base al centro del cluster
    centers = gmm.means_
    name_map = {}
    for i, (cx, cy) in enumerate(centers):
        if cx >= 0 and cy >= 0:
            name_map[i] = "Goldilocks"
        elif cx < 0 and cy >= 0:
            name_map[i] = "Fuga verso la qualità"
        elif cx >= 0 and cy < 0:
            name_map[i] = "Boom con tassi in salita"
        else:
            name_map[i] = "Stagflazione / Crisi"

    # risolvi conflitti (due cluster nello stesso quadrante)
    used = set()
    all_names = list(REGIME_COLORS.keys())
    final_map = {}
    # prima assegnazione diretta
    for i in sorted(name_map, key=lambda k: -np.linalg.norm(centers[k])):
        name = name_map[i]
        if name not in used:
            final_map[i] = name
            used.add(name)
        else:
            for fallback in all_names:
                if fallback not in used:
                    final_map[i] = fallback
                    used.add(fallback)
                    break
    name_map = final_map

    fig = go.Figure()

    for i in range(n_clusters):
        mask = labels == i
        regime = name_map.get(i, f"Regime {i}")
        color = REGIME_COLORS.get(regime, "#8b949e")
        sub = df[mask]
        fig.add_trace(go.Scatter(
            x=sub["stocks"], y=sub["bonds"],
            mode="markers+text",
            text=[str(int(y))[-2:] for y in sub["year"]],
            textposition="top center",
            textfont=dict(size=9, color=color, family=FONT_MONO),
            marker=dict(size=9, color=color, opacity=0.85,
                        line=dict(width=0.5, color="#0d1117")),
            name=f"{regime} ({mask.sum()} anni)",
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>"
                "Azioni: %{x:+.1f}%<br>"
                "Bond: %{y:+.1f}%<br>"
                f"Regime: {regime}"
                "<extra></extra>"
            ),
            customdata=sub[["year"]].values,
        ))

        # ellissi 1σ e 2σ con riempimento sfumato
        cov = gmm.covariances_[i]
        mean = centers[i]
        eigvals, eigvecs = np.linalg.eigh(cov)
        # hex → rgb
        r_c, g_c, b_c = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)
        # 2σ prima (sfondo più chiaro), poi 1σ sopra
        for n_std, fill_alpha, line_alpha in [(2, 0.07, 0.2), (1, 0.15, 0.4)]:
            theta = np.linspace(0, 2 * np.pi, 100)
            ellipse = np.column_stack([np.cos(theta), np.sin(theta)])
            ellipse = ellipse @ np.diag(np.sqrt(eigvals) * n_std) @ eigvecs.T + mean
            fig.add_trace(go.Scatter(
                x=ellipse[:, 0], y=ellipse[:, 1],
                mode="none",
                fill="toself",
                fillcolor=f"rgba({r_c},{g_c},{b_c},{fill_alpha})",
                line=dict(color=f"rgba({r_c},{g_c},{b_c},{line_alpha})", width=1.5),
                showlegend=False, hoverinfo="skip",
            ))

    # linee di riferimento
    fig.add_vline(x=0, line=dict(color="#444c56", dash="dot", width=1))
    fig.add_hline(y=0, line=dict(color="#444c56", dash="dot", width=1))

    fig.update_layout(
        title=dict(
            text=(f"<b>1. Regimi di Mercato</b> — Clustering GMM ({n_clusters} regimi)<br>"
                  f"<sup>BIC ottimale: {best_n} comp. | Usati {n_clusters} per interpretabilità</sup>"),
            font=dict(family="Georgia, serif", size=20, color=TEXT_COL),
            x=0.5, xanchor="center",
        ),
        xaxis=dict(title="Rendimento Azioni (%)", gridcolor=GRID_COL, zeroline=False,
                    ticksuffix="%", tickfont=dict(family=FONT_MONO, size=12, color=MUTED_COL),
                    title_font=dict(family=FONT_TEXT, size=14, color=MUTED_COL)),
        yaxis=dict(title="Rendimento Bond (%)", gridcolor=GRID_COL, zeroline=False,
                    ticksuffix="%", tickfont=dict(family=FONT_MONO, size=12, color=MUTED_COL),
                    title_font=dict(family=FONT_TEXT, size=14, color=MUTED_COL)),
        plot_bgcolor=PLOT_BG, paper_bgcolor=PAPER_BG,
        legend=dict(font=dict(family=FONT_TEXT, size=13, color=TEXT_COL),
                    bgcolor=PLOT_BG, bordercolor=GRID_COL, borderwidth=1),
        hoverlabel=dict(bgcolor=PAPER_BG, bordercolor=GRID_COL,
                        font=dict(family=FONT_MONO, size=14, color=TEXT_COL)),
        autosize=True, height=650, margin=dict(t=90, b=60, l=60, r=30),
    )

    regime_counts = {}
    for i in range(n_clusters):
        regime = name_map[i]
        regime_counts[regime] = int((labels == i).sum())

    return fig, regime_counts


# ════════════════════════════════════════════════════════════════════════════
#  ANALISI 2 — Matrice di Transizione Markov
# ════════════════════════════════════════════════════════════════════════════

def _assign_quadrant(row):
    s, b = row["stocks"], row["bonds"]
    if s >= 0 and b >= 0: return 0   # Azioni+ Bond+
    if s < 0  and b >= 0: return 1   # Azioni- Bond+
    if s < 0  and b < 0:  return 2   # Azioni- Bond-
    return 3                          # Azioni+ Bond-


def analysis_markov_transitions(df: pd.DataFrame) -> tuple:
    df = df.sort_values("year").copy()
    df["quadrant"] = df.apply(_assign_quadrant, axis=1)

    # matrice di transizione
    n = 4
    counts = np.zeros((n, n), dtype=int)
    quads = df["quadrant"].values
    for i in range(len(quads) - 1):
        counts[quads[i], quads[i + 1]] += 1

    # normalizza righe
    row_sums = counts.sum(axis=1, keepdims=True)
    probs = np.where(row_sums > 0, counts / row_sums * 100, 0)

    # conteggi per quadrante
    quad_counts = [int((df["quadrant"] == q).sum()) for q in range(n)]

    text_vals = [[f"{probs[i, j]:.0f}%<br>({counts[i, j]})" for j in range(n)]
                 for i in range(n)]

    labels_with_counts = [f"{QUADRANT_NAMES[i]}<br>({quad_counts[i]} anni)" for i in range(n)]

    fig = go.Figure(data=go.Heatmap(
        z=probs,
        x=labels_with_counts,
        y=labels_with_counts,
        text=text_vals,
        texttemplate="%{text}",
        textfont=dict(size=14, color="white", family=FONT_MONO),
        colorscale=[[0, PLOT_BG], [0.5, "#1f6feb"], [1, "#58a6ff"]],
        showscale=True,
        colorbar=dict(title=dict(text="Prob %", font=dict(color=MUTED_COL)),
                      ticksuffix="%", tickfont=dict(color=MUTED_COL)),
        hovertemplate=(
            "Da: %{y}<br>A: %{x}<br>"
            "Probabilità: %{z:.1f}%<extra></extra>"
        ),
    ))

    fig.update_layout(
        title=dict(
            text=(f"<b>2. Matrice di Transizione Markov</b><br>"
                  f"<sup>Probabilità di passaggio da un quadrante all'altro nell'anno successivo "
                  f"({len(df)-1} transizioni)</sup>"),
            font=dict(family="Georgia, serif", size=20, color=TEXT_COL),
            x=0.5, xanchor="center",
        ),
        xaxis=dict(title="Anno successivo →", side="bottom",
                    tickfont=dict(family=FONT_MONO, size=11, color=TEXT_COL),
                    title_font=dict(family=FONT_MONO, size=12, color=MUTED_COL)),
        yaxis=dict(title="Anno corrente →", autorange="reversed",
                    tickfont=dict(family=FONT_MONO, size=11, color=TEXT_COL),
                    title_font=dict(family=FONT_MONO, size=12, color=MUTED_COL)),
        plot_bgcolor=PLOT_BG, paper_bgcolor=PAPER_BG,
        autosize=True, height=600, margin=dict(t=90, b=80, l=120, r=30),
    )

    trans_data = {
        "probs": probs,
        "counts": counts,
        "quad_names": QUADRANT_NAMES,
    }

    return fig, trans_data


# ════════════════════════════════════════════════════════════════════════════
#  ANALISI 3 — Correlazione Rolling Azioni-Bond
# ════════════════════════════════════════════════════════════════════════════

def analysis_rolling_correlation(df: pd.DataFrame) -> go.Figure:
    df = df.sort_values("year").copy()
    window = 10

    years = df["year"].values
    stocks = df["stocks"].values
    bonds = df["bonds"].values

    roll_corr = []
    roll_years = []
    for i in range(window, len(years) + 1):
        s_win = stocks[i - window:i]
        b_win = bonds[i - window:i]
        r = np.corrcoef(s_win, b_win)[0, 1]
        roll_corr.append(r)
        roll_years.append(years[i - 1])

    roll_corr = np.array(roll_corr)
    roll_years = np.array(roll_years)

    fig = go.Figure()

    # area positiva (rosso) e negativa (verde)
    pos_corr = np.where(roll_corr >= 0, roll_corr, 0)
    neg_corr = np.where(roll_corr < 0, roll_corr, 0)

    fig.add_trace(go.Scatter(
        x=roll_years, y=pos_corr,
        fill="tozeroy", fillcolor="rgba(248, 81, 73, 0.25)",
        line=dict(width=0), showlegend=True,
        name="Area rossa = azioni e bond si muovono insieme (diversificazione NON funziona)",
        hoverinfo="skip",
    ))
    fig.add_trace(go.Scatter(
        x=roll_years, y=neg_corr,
        fill="tozeroy", fillcolor="rgba(63, 185, 80, 0.25)",
        line=dict(width=0), showlegend=True,
        name="Area verde = azioni e bond si muovono in direzioni opposte (diversificazione funziona)",
        hoverinfo="skip",
    ))
    fig.add_trace(go.Scatter(
        x=roll_years, y=roll_corr,
        mode="lines",
        line=dict(color="#58a6ff", width=2.5),
        name="Linea blu = valore della correlazione (media ultimi 10 anni)",
        hovertemplate="<b>%{x}</b><br>Correlazione: %{y:.2f}<extra></extra>",
    ))

    fig.add_hline(y=0, line=dict(color="#444c56", dash="dot", width=1))

    # annotazioni
    annotations = [
        (1945, "Fine WWII"),
        (1980, "Volcker: tassi al 20%"),
        (2000, "Inversione correlazione"),
        (2022, "Ritorno inflazione"),
    ]
    for yr, label in annotations:
        if yr in roll_years:
            idx = np.where(roll_years == yr)[0][0]
            fig.add_annotation(
                x=yr, y=roll_corr[idx],
                text=label,
                showarrow=True, arrowhead=2, arrowsize=0.8,
                arrowcolor=MUTED_COL, arrowwidth=1,
                font=dict(size=11, color=TEXT_COL, family=FONT_TEXT),
                bgcolor=PAPER_BG, bordercolor=GRID_COL, borderwidth=1, borderpad=4,
            )

    fig.update_layout(
        title=dict(
            text=(f"<b>3. Correlazione Rolling Azioni-Bond</b><br>"
                  f"<br>"
                  f"<span style='font-size:14px;color:#8b949e;'>"
                  f"Finestra mobile di {window} anni — Quando la correlazione è negativa, "
                  f"le obbligazioni proteggono dai ribassi azionari</span>"),
            font=dict(family="Georgia, serif", size=20, color=TEXT_COL),
            x=0.5, xanchor="center",
            yanchor="top", y=0.98,
        ),
        xaxis=dict(title="Anno", gridcolor=GRID_COL,
                    tickfont=dict(family=FONT_MONO, size=12, color=MUTED_COL),
                    title_font=dict(family=FONT_TEXT, size=14, color=MUTED_COL)),
        yaxis=dict(title="Correlazione di Pearson", range=[-1, 1], gridcolor=GRID_COL,
                    tickfont=dict(family=FONT_MONO, size=12, color=MUTED_COL),
                    title_font=dict(family=FONT_TEXT, size=14, color=MUTED_COL)),
        plot_bgcolor=PLOT_BG, paper_bgcolor=PAPER_BG,
        legend=dict(font=dict(family=FONT_TEXT, size=13, color=TEXT_COL),
                    bgcolor=PLOT_BG, bordercolor=GRID_COL, borderwidth=1,
                    orientation="h", yanchor="top", y=-0.12, xanchor="center", x=0.5),
        hoverlabel=dict(bgcolor=PAPER_BG, bordercolor=GRID_COL,
                        font=dict(family=FONT_MONO, size=14, color=TEXT_COL)),
        autosize=True, height=700, margin=dict(t=140, b=100, l=60, r=30),
    )
    return fig


# ════════════════════════════════════════════════════════════════════════════
#  ANALISI 4 — CAPE come Predittore
# ════════════════════════════════════════════════════════════════════════════

def analysis_cape_predictor(df: pd.DataFrame, shiller_ext: pd.DataFrame) -> tuple:
    # merge CAPE e CPI con rendimenti
    merged = df.merge(shiller_ext[["year", "cape", "inflation"]], on="year", how="inner")
    merged = merged.dropna(subset=["cape"]).sort_values("year").reset_index(drop=True)

    # calcolo rendimento reale annualizzato a 10 anni
    records = []
    for i, row in merged.iterrows():
        yr = int(row["year"])
        future = df[(df["year"] > yr) & (df["year"] <= yr + 10)]
        if len(future) == 10:
            cum = np.prod(1 + future["stocks"].values / 100)
            ann_nominal = (cum ** (1 / 10) - 1) * 100
            # inflazione media nei 10 anni
            inf_data = merged[(merged["year"] > yr) & (merged["year"] <= yr + 10)]
            if len(inf_data) >= 8 and "inflation" in inf_data.columns:
                avg_inf = inf_data["inflation"].mean()
                ann_real = ann_nominal - avg_inf
            else:
                ann_real = ann_nominal  # fallback: nominale
            records.append({
                "year": yr, "cape": row["cape"],
                "fwd_10yr_real": round(ann_real, 2),
                "fwd_10yr_nom": round(ann_nominal, 2),
            })

    fwd = pd.DataFrame(records)
    if len(fwd) < 5:
        print("  [CAPE] Dati insufficienti per analisi CAPE")
        return go.Figure()

    # regressione lineare
    from numpy.polynomial import polynomial as P
    coeffs = np.polyfit(fwd["cape"], fwd["fwd_10yr_real"], 1)
    x_line = np.linspace(fwd["cape"].min() - 2, fwd["cape"].max() + 2, 100)
    y_line = np.polyval(coeffs, x_line)
    r_squared = np.corrcoef(fwd["cape"], fwd["fwd_10yr_real"])[0, 1] ** 2

    # colora per decennio
    fwd["decade"] = (fwd["year"] // 10) * 10

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=x_line, y=y_line,
        mode="lines",
        line=dict(color="#f85149", width=2, dash="dash"),
        name=f"Regressione (R²={r_squared:.2f})",
        hoverinfo="skip",
    ))

    last_complete_year = int(fwd["year"].max())
    fwd["decade"] = (fwd["year"] // 10) * 10
    for decade, group in fwd.groupby("decade"):
        decade_label = f"{int(decade)}s"
        color = DECADE_COLORS.get(decade_label, "#8b949e")
        fig.add_trace(go.Scatter(
            x=group["cape"], y=group["fwd_10yr_real"],
            mode="markers+text",
            text=[str(int(y))[-2:] for y in group["year"]],
            textposition="top center",
            textfont=dict(size=8, color=color, family=FONT_MONO),
            marker=dict(size=9, color=color, opacity=0.85,
                        line=dict(width=0.5, color="#0d1117")),
            name=f"{decade_label} (rendimento futuro noto)",
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>"
                "CAPE: %{x:.1f}<br>"
                "Rend. reale 10yr: %{y:+.1f}%/anno"
                "<extra></extra>"
            ),
            customdata=group[["year"]].values,
        ))

    # Anni recenti: sappiamo il CAPE ma non ancora il rendimento dei 10 anni successivi
    recent_years = merged[merged["year"] > fwd["year"].max()].copy()
    if len(recent_years) > 0:
        predicted_y = np.polyval(coeffs, recent_years["cape"].values)
        first_recent = int(recent_years["year"].min())
        last_recent = int(recent_years["year"].max())
        fig.add_trace(go.Scatter(
            x=recent_years["cape"], y=predicted_y,
            mode="markers+text",
            text=[str(int(y)) for y in recent_years["year"]],
            textposition="top center",
            textfont=dict(size=11, color="#f0883e", family=FONT_MONO),
            marker=dict(size=13, color="#f0883e", opacity=0.9,
                        symbol="diamond",
                        line=dict(width=1.5, color="#0d1117")),
            name=(f"{first_recent}–{last_recent}: il rendimento dei prossimi 10 anni "
                  f"non lo sapremo fino al {last_recent + 10}"),
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>"
                "CAPE: %{x:.1f}<br>"
                "Rendimento futuro a 10 anni: non lo sapremo fino al %{customdata[0]:.0f}+10<br>"
                "(posizionato sulla previsione storica)"
                "<extra></extra>"
            ),
            customdata=recent_years[["year"]].values,
        ))

    # linee di riferimento CAPE
    y_top = fwd["fwd_10yr_real"].max() + 1
    for cape_val, label, color in [(15, "Mediana storica", "#3fb950"),
                                    (25, "Costoso", "#d29922"),
                                    (35, "Bolla", "#f85149")]:
        fig.add_vline(x=cape_val, line=dict(color=color, dash="dot", width=1), opacity=0.5)
        fig.add_annotation(x=cape_val, y=y_top,
                           text=f"CAPE={cape_val}<br>{label}",
                           showarrow=False,
                           font=dict(size=10, color=color, family=FONT_MONO))

    n_indep = max(1, len(fwd) // 10)
    fig.update_layout(
        title=dict(
            text=(f"<b>4. CAPE di Shiller come Predittore</b><br>"
                  f"<br>"
                  f"<span style='font-size:14px;color:#8b949e;'>"
                  f"Quanto era \"costoso\" il mercato in ogni anno (asse X) vs "
                  f"quanto ha reso nei 10 anni successivi (asse Y)</span>"),
            font=dict(family="Georgia, serif", size=20, color=TEXT_COL),
            x=0.5, xanchor="center",
            yanchor="top", y=0.98,
        ),
        xaxis=dict(title="CAPE — più è alto, più il mercato è \"costoso\"",
                    gridcolor=GRID_COL,
                    tickfont=dict(family=FONT_MONO, size=12, color=MUTED_COL),
                    title_font=dict(family=FONT_TEXT, size=14, color=MUTED_COL)),
        yaxis=dict(title="Rendimento reale annualizzato nei 10 anni dopo (%)",
                    gridcolor=GRID_COL, ticksuffix="%",
                    tickfont=dict(family=FONT_MONO, size=12, color=MUTED_COL),
                    title_font=dict(family=FONT_TEXT, size=14, color=MUTED_COL)),
        plot_bgcolor=PLOT_BG, paper_bgcolor=PAPER_BG,
        legend=dict(font=dict(family=FONT_TEXT, size=12, color=TEXT_COL),
                    bgcolor=PLOT_BG, bordercolor=GRID_COL, borderwidth=1,
                    orientation="h", yanchor="top", y=-0.12, xanchor="center", x=0.5),
        hoverlabel=dict(bgcolor=PAPER_BG, bordercolor=GRID_COL,
                        font=dict(family=FONT_MONO, size=14, color=TEXT_COL)),
        autosize=True, height=1100, margin=dict(t=140, b=120, l=60, r=30),
    )

    cape_info = {
        "n_indep": n_indep,
        "cutoff_year": int(fwd["year"].max()),
    }
    if len(recent_years) > 0:
        cape_info["recent_cape_min"] = float(recent_years["cape"].min())
        cape_info["recent_cape_max"] = float(recent_years["cape"].max())

    return fig, cape_info


# ════════════════════════════════════════════════════════════════════════════
#  ANALISI 5 — Mean Reversion / Rendimenti Condizionali
# ════════════════════════════════════════════════════════════════════════════

def analysis_mean_reversion(df_full: pd.DataFrame) -> tuple[go.Figure, dict]:
    df = df_full.sort_values("year").copy()

    # definisci bucket per il rendimento azionario dell'anno corrente
    bins = [(-999, -10, "Crollo (< -10%)"),
            (-10, 0, "Negativo (-10% a 0%)"),
            (0, 20, "Moderato (0% a +20%)"),
            (20, 999, "Boom (> +20%)")]

    df["next_stocks"] = df["stocks"].shift(-1)
    df_pairs = df.dropna(subset=["next_stocks"]).copy()

    # calcola statistiche per bucket (per la previsione 2026)
    bucket_stats = {}
    for lo, hi, label in bins:
        mask = (df_pairs["stocks"] >= lo) & (df_pairs["stocks"] < hi)
        sub = df_pairs[mask]
        if len(sub) >= 2:
            vals = sub["next_stocks"].values
            bucket_stats[(lo, hi)] = {
                "label": label, "n": len(sub),
                "median": float(np.median(vals)),
                "mean": float(np.mean(vals)),
                "pct_positive": float((vals > 0).sum() / len(vals) * 100),
                "q25": float(np.percentile(vals, 25)),
                "q75": float(np.percentile(vals, 75)),
            }

    fig = go.Figure()
    colors = ["#f85149", "#d29922", "#58a6ff", "#3fb950"]

    for idx, (lo, hi, label) in enumerate(bins):
        mask = (df_pairs["stocks"] >= lo) & (df_pairs["stocks"] < hi)
        sub = df_pairs[mask]
        if len(sub) < 2:
            continue

        vals = sub["next_stocks"].values
        fig.add_trace(go.Box(
            y=vals, name=f"{label}<br>(n={len(sub)})",
            marker_color=colors[idx],
            boxpoints="all", jitter=0.4, pointpos=-1.5,
            marker=dict(size=5, opacity=0.6),
            hovertemplate=(
                "%{customdata[0]}: azioni %{customdata[1]:+.1f}%<br>"
                "→ anno dopo: %{y:+.1f}%<extra></extra>"
            ),
            customdata=np.column_stack([sub["year"].values, sub["stocks"].values]),
        ))

    # linea media incondizionata
    unconditional_mean = df_pairs["next_stocks"].mean()
    fig.add_hline(y=unconditional_mean,
                  line=dict(color="#58a6ff", dash="dash", width=1.5),
                  annotation_text=f"Media generale: {unconditional_mean:+.1f}%",
                  annotation_font=dict(color=MUTED_COL, size=12, family=FONT_MONO))
    fig.add_hline(y=0, line=dict(color="#444c56", dash="dot", width=1))

    # previsione 2026 basata sull'ultimo anno
    last_year = int(df["year"].max())
    last_return = float(df.loc[df["year"] == last_year, "stocks"].values[0])
    prediction_bucket = None
    for lo, hi in bucket_stats:
        if lo <= last_return < hi:
            prediction_bucket = bucket_stats[(lo, hi)]
            break

    prediction_info = {
        "last_year": last_year,
        "last_return": last_return,
        "next_year": last_year + 1,
        "bucket": prediction_bucket,
    }

    # annotazione previsione sul grafico
    if prediction_bucket:
        fig.add_annotation(
            xref="paper", yref="paper", x=1.0, y=1.0,
            text=(f"<b>{last_year + 1}?</b>  Il {last_year} ha chiuso a "
                  f"{last_return:+.1f}% ({prediction_bucket['label']})<br>"
                  f"Storicamente: mediana anno dopo = {prediction_bucket['median']:+.1f}%, "
                  f"positivo nel {prediction_bucket['pct_positive']:.0f}% dei casi"),
            showarrow=False, align="right",
            font=dict(size=12, color="#f0883e", family=FONT_TEXT),
            bgcolor=PAPER_BG, bordercolor="#f0883e", borderwidth=1, borderpad=8,
        )

    fig.update_layout(
        title=dict(
            text=("<b>5. Mean Reversion</b> — Cosa succede l'anno dopo?<br>"
                  "<br>"
                  "<span style='font-size:14px;color:#8b949e;'>"
                  "Ogni colonna mostra la distribuzione del rendimento azionario "
                  "nell'anno successivo, raggruppata per tipo di anno corrente. "
                  "I punti sono i singoli anni storici.</span>"),
            font=dict(family="Georgia, serif", size=20, color=TEXT_COL),
            x=0.5, xanchor="center",
            yanchor="top", y=0.98,
        ),
        yaxis=dict(title="Rendimento Azioni anno successivo (%)",
                    gridcolor=GRID_COL, zeroline=False, ticksuffix="%",
                    tickfont=dict(family=FONT_MONO, size=12, color=MUTED_COL),
                    title_font=dict(family=FONT_TEXT, size=14, color=MUTED_COL)),
        xaxis=dict(tickfont=dict(family=FONT_TEXT, size=12, color=TEXT_COL)),
        plot_bgcolor=PLOT_BG, paper_bgcolor=PAPER_BG,
        showlegend=False,
        hoverlabel=dict(bgcolor=PAPER_BG, bordercolor=GRID_COL,
                        font=dict(family=FONT_MONO, size=14, color=TEXT_COL)),
        autosize=True, height=700, margin=dict(t=140, b=60, l=60, r=30),
    )
    return fig, prediction_info


# ════════════════════════════════════════════════════════════════════════════
#  ANALISI 6 — Autocorrelazione e Cicli
# ════════════════════════════════════════════════════════════════════════════

def analysis_autocorrelation(df: pd.DataFrame) -> tuple:
    df = df.sort_values("year").copy()
    max_lag = 15
    n = len(df)
    conf = 1.96 / np.sqrt(n)

    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=[
            "ACF Rendimenti Azioni", "ACF Rendimenti Bond",
            "Spettro di Potenza Azioni", "Spettro di Potenza Bond"
        ],
        vertical_spacing=0.15, horizontal_spacing=0.1,
    )

    acf_info = {}

    for col_idx, (series_name, series_label) in enumerate([("stocks", "Azioni"), ("bonds", "Bond")]):
        vals = df[series_name].values
        vals_centered = vals - vals.mean()

        # ACF
        acf_vals = []
        for lag in range(1, max_lag + 1):
            if lag < n:
                r = np.corrcoef(vals_centered[:-lag], vals_centered[lag:])[0, 1]
                acf_vals.append(r)
            else:
                acf_vals.append(0)

        lags = list(range(1, max_lag + 1))
        bar_colors = ["#f85149" if abs(v) > conf else "#58a6ff" for v in acf_vals]

        acf_info[series_label] = {
            "significant": [(lg, val) for lg, val in zip(lags, acf_vals) if abs(val) > conf],
            "conf": conf,
        }

        fig.add_trace(go.Bar(
            x=lags, y=acf_vals, marker_color=bar_colors,
            name=f"ACF {series_label}", showlegend=False,
            hovertemplate="Lag %{x}: r = %{y:.3f}<extra></extra>",
        ), row=1, col=col_idx + 1)

        # bande di confidenza
        fig.add_hline(y=conf, line=dict(color="#f85149", dash="dash", width=1),
                      row=1, col=col_idx + 1)
        fig.add_hline(y=-conf, line=dict(color="#f85149", dash="dash", width=1),
                      row=1, col=col_idx + 1)
        fig.add_hline(y=0, line=dict(color="#444c56", dash="dot", width=1),
                      row=1, col=col_idx + 1)

        # FFT
        fft_vals = np.fft.rfft(vals_centered)
        power = np.abs(fft_vals) ** 2
        freqs = np.fft.rfftfreq(n, d=1)  # freq in cicli/anno

        # escludi DC (freq 0)
        freqs = freqs[1:]
        power = power[1:]
        periods = 1 / freqs  # periodo in anni

        fig.add_trace(go.Scatter(
            x=periods, y=power,
            mode="lines",
            line=dict(color="#58a6ff", width=2),
            name=f"Spettro {series_label}", showlegend=False,
            hovertemplate="Periodo: %{x:.1f} anni<br>Potenza: %{y:.0f}<extra></extra>",
        ), row=2, col=col_idx + 1)

    # aggiorna assi
    for col_idx in [1, 2]:
        fig.update_xaxes(title_text="Lag (anni)", row=1, col=col_idx,
                         gridcolor=GRID_COL,
                         tickfont=dict(family=FONT_MONO, size=9, color=MUTED_COL),
                         title_font=dict(family=FONT_MONO, size=10, color=MUTED_COL))
        fig.update_yaxes(title_text="Autocorrelazione", row=1, col=col_idx,
                         gridcolor=GRID_COL, range=[-0.4, 0.4],
                         tickfont=dict(family=FONT_MONO, size=9, color=MUTED_COL),
                         title_font=dict(family=FONT_MONO, size=10, color=MUTED_COL))
        fig.update_xaxes(title_text="Periodo (anni)", row=2, col=col_idx,
                         gridcolor=GRID_COL, range=[2, 60],
                         tickfont=dict(family=FONT_MONO, size=9, color=MUTED_COL),
                         title_font=dict(family=FONT_MONO, size=10, color=MUTED_COL))
        fig.update_yaxes(title_text="Potenza", row=2, col=col_idx,
                         gridcolor=GRID_COL,
                         tickfont=dict(family=FONT_MONO, size=9, color=MUTED_COL),
                         title_font=dict(family=FONT_MONO, size=10, color=MUTED_COL))

    fig.update_layout(
        title=dict(
            text=("<b>6. Autocorrelazione e Cicli</b><br>"
                  "<sup>I rendimenti azionari sono prevedibili dai rendimenti passati? "
                  "Barre rosse = statisticamente significativi (p&lt;0.05)</sup>"),
            font=dict(family="Georgia, serif", size=20, color=TEXT_COL),
            x=0.5, xanchor="center",
        ),
        plot_bgcolor=PLOT_BG, paper_bgcolor=PAPER_BG,
        autosize=True, height=700,
        margin=dict(t=90, b=60, l=60, r=30),
    )
    # colora titoli sottografici
    for ann in fig.layout.annotations:
        ann.font = dict(family=FONT_TEXT, size=15, color=TEXT_COL)

    return fig, acf_info


# ════════════════════════════════════════════════════════════════════════════
#  HTML ASSEMBLY
# ════════════════════════════════════════════════════════════════════════════

SECTION_TEXT = {
    1: {
        "intro": (
            "Un algoritmo di machine learning (<b>Gaussian Mixture Model</b>) "
            "analizza tutti gli anni e raggruppa automaticamente quelli con rendimenti simili, "
            "scoprendo 4 \"regimi\" ricorrenti. "
            "Ogni zona colorata e sfumata rappresenta un regime — più è ampia, "
            "più i rendimenti in quel regime sono variabili.<br><br>"
            "I 4 regimi sono:<br>"
            "<span style='color:#3fb950'>&#9679;</span> <b>Goldilocks</b> — "
            "Azioni e bond salgono entrambi. L'economia va bene, l'inflazione è sotto controllo.<br>"
            "<span style='color:#58a6ff'>&#9679;</span> <b>Fuga verso la qualità</b> — "
            "Le azioni scendono ma le obbligazioni salgono. Succede nelle crisi: "
            "gli investitori vendono le azioni (rischiose) e comprano titoli di Stato "
            "(\"sicuri\"), facendone salire il prezzo. Esempio: 2008.<br>"
            "<span style='color:#d29922'>&#9679;</span> <b>Boom con tassi in salita</b> — "
            "Le azioni salgono ma le obbligazioni scendono. L'economia è forte, "
            "le banche centrali alzano i tassi e i prezzi dei bond calano.<br>"
            "<span style='color:#f85149'>&#9679;</span> <b>Stagflazione / Crisi</b> — "
            "Azioni e bond scendono entrambi. Lo scenario peggiore: "
            "l'inflazione alta erode sia azioni che obbligazioni. Esempio: 1974, 2022."
        ),
        "takeaway": "",  # verrà aggiornato dinamicamente nel main con i dati dei regimi
    },
    2: {
        "intro": (
            "Una <b>catena di Markov</b> risponde alla domanda: "
            "\"Dato il quadrante di quest'anno, in quale quadrante finiremo l'anno prossimo?\" "
            "Ogni cella mostra la probabilità (e il numero di transizioni osservate) "
            "di passare dal quadrante della riga a quello della colonna."
        ),
        "takeaway": "",  # verrà aggiornato dinamicamente nel main con i dati di Markov
    },
    3: {
        "intro": (
            "Immagina di guardare azioni e obbligazioni negli ultimi 10 anni: "
            "si muovono insieme (quando una sale, sale anche l'altra) o in direzioni opposte? "
            "Questo è ciò che misura la <b>correlazione</b>.<br><br>"
            "La <b>linea blu</b> mostra questa correlazione calcolata su una finestra mobile "
            "di 10 anni: per ogni anno sul grafico, guarda i 10 anni precedenti e calcola "
            "quanto azioni e bond si sono mosse insieme.<br><br>"
            "Le <b>aree colorate</b> evidenziano i periodi:<br>"
            "<span style='color:#f85149'>&#9679;</span> <b>Area rossa</b> (correlazione positiva) — "
            "Azioni e bond si muovono nella stessa direzione. "
            "Se le azioni scendono, scendono anche i bond: la diversificazione <b>non funziona</b>.<br>"
            "<span style='color:#3fb950'>&#9679;</span> <b>Area verde</b> (correlazione negativa) — "
            "Quando le azioni scendono, i bond tendono a salire. "
            "La diversificazione <b>funziona</b>: i bond proteggono il portafoglio."
        ),
        "takeaway": (
            "Per gran parte del '900 la correlazione era <b>positiva</b>: "
            "l'inflazione dominava tutto, facendo muovere azioni e bond insieme. "
            "Intorno al <b>2000</b> c'è stato un cambio storico: la correlazione è diventata "
            "negativa, e per 20 anni le obbligazioni hanno protetto dai crolli azionari. "
            "Nel <b>2022</b>, con il ritorno dell'inflazione, la correlazione è tornata positiva "
            "e la diversificazione ha smesso di funzionare: sia azioni che bond hanno perso."
        ),
    },
    4: {
        "intro": "",  # verrà aggiornato dinamicamente nel main con i dati CAPE
        "takeaway": "",  # verrà aggiornato dinamicamente nel main con i dati CAPE
    },
    5: {
        "intro": (
            "I mercati hanno memoria? Quando le azioni crollano, tendono a rimbalzare "
            "l'anno dopo — o il crollo continua?<br><br>"
            "Per scoprirlo, raggruppiamo tutti gli anni in 4 categorie in base al rendimento "
            "azionario, e per ciascuna guardiamo cosa è successo <b>l'anno dopo</b>:<br>"
            "<span style='color:#f85149'>&#9679;</span> <b>Crollo</b> (sotto -10%) — "
            "anni come 1929, 1974, 2008<br>"
            "<span style='color:#d29922'>&#9679;</span> <b>Negativo</b> (tra -10% e 0%) — "
            "anni di calo moderato<br>"
            "<span style='color:#58a6ff'>&#9679;</span> <b>Moderato</b> (tra 0% e +20%) — "
            "la situazione più comune<br>"
            "<span style='color:#3fb950'>&#9679;</span> <b>Boom</b> (sopra +20%) — "
            "anni eccezionali<br><br>"
            "Ogni \"scatola\" mostra dove si concentra la maggior parte dei rendimenti "
            "dell'anno successivo (dal 25° al 75° percentile), la linea al centro è la mediana, "
            "e i punti sono tutti i singoli anni storici."
        ),
        "takeaway": "",  # verrà aggiornato dinamicamente nel main con i dati di previsione
    },
    6: {
        "intro": (
            "Domanda fondamentale: <b>i rendimenti passati aiutano a prevedere quelli futuri?</b><br><br>"
            "I grafici in alto (<b>ACF</b>) rispondono così: ogni barra misura quanto "
            "il rendimento di un anno è correlato con quello di N anni prima. "
            "\"Lag 1\" = confronto con l'anno prima, \"Lag 2\" = due anni prima, ecc. "
            "Se una barra supera le linee rosse tratteggiate, quella correlazione è "
            "statisticamente significativa (non è dovuta al caso).<br><br>"
            "I grafici in basso (<b>Spettro di potenza</b>) cercano <b>cicli ripetitivi</b>: "
            "se il mercato avesse un ciclo regolare (es. \"ogni 15 anni c'è un crollo\"), "
            "vedremmo un picco in corrispondenza di quel periodo."
        ),
        "takeaway": "",  # verrà aggiornato dinamicamente nel main con i dati ACF reali
    },
}

def build_caveats_html(n_years, first_year):
    return f"""
<div style="max-width:900px;margin:40px auto;padding:30px;
            background:#161b22;border:1px solid #30363d;border-radius:8px;">
  <h2 style="color:#f0f6fc;font-family:Georgia,serif;margin-top:0;">
    Caveat e Note Metodologiche
  </h2>
  <ol style="color:#c9d1d9;font-size:16px;line-height:1.9;">
    <li><b>Campione piccolo (N ≈ {n_years}):</b> Con ~{n_years} osservazioni annuali,
        tutti i risultati hanno intervalli di confidenza ampi. I pattern
        mostrati sono suggestivi, non leggi statistiche provate.</li>
    <li><b>Non-stazionarietà:</b> L'economia USA del {first_year} è fondamentalmente
        diversa da quella del {TODAY.year}. Gold standard, politica monetaria,
        struttura dei mercati e globalizzazione sono cambiati radicalmente.</li>
    <li><b>Survivorship bias:</b> Il mercato USA ha avuto la migliore performance
        azionaria del XX secolo. Analisi simili per Giappone, Germania o Russia
        racconterebbero storie molto diverse.</li>
    <li><b>Finestre sovrapposte (CAPE):</b> I rendimenti a 10 anni calcolati
        per anni adiacenti condividono 9 anni di dati su 10, inflazionando
        la significatività statistica apparente.</li>
    <li><b>Lookahead bias nei cluster:</b> Il GMM è fittato sull'intero dataset
        incluso il futuro. Un investitore nel 1950 non poteva sapere in che
        regime si trovava.</li>
    <li><b>Approssimazione duration:</b> I rendimenti obbligazionari sono stimati
        con un modello di duration, non da indici di total return reali.
        L'approssimazione ignora convexity, roll-down e reinvestimento cedole.</li>
    <li><b>Data splicing:</b> La serie azionaria combina stime Cowles Commission
        (1910-1925), ricostruzioni Shiller (1926-1987) e S&P 500 Total Return
        Index (1988+). I punti di giunzione possono creare artefatti.</li>
    <li><b>No costi e tasse:</b> Tutti i rendimenti sono lordi. I rendimenti
        reali di un investitore sarebbero inferiori per costi di transazione,
        tasse e errori comportamentali.</li>
  </ol>
</div>
"""


def build_html(figures: list[tuple[int, go.Figure]], caveats_html: str = "") -> str:
    plotly_divs = []
    for i, (section_num, fig) in enumerate(figures):
        # primo grafico include plotly.js, gli altri no
        include_js = "cdn" if i == 0 else False
        div_html = fig.to_html(full_html=False, include_plotlyjs=include_js)
        texts = SECTION_TEXT.get(section_num, {})
        intro = texts.get("intro", "")
        takeaway = texts.get("takeaway", "")

        section = f"""
<div id="section-{section_num}" style="max-width:1200px;margin:30px auto;padding:0 20px;">
  <div style="background:#161b22;border:1px solid #30363d;border-radius:8px;
              padding:20px;margin-bottom:10px;">
    <p style="color:#c9d1d9;font-size:17px;
              line-height:1.8;margin:0;">{intro}</p>
  </div>
  {div_html}
  <div style="background:#0d1117;border-left:3px solid #58a6ff;
              padding:12px 20px;margin:10px 0 40px 0;border-radius:0 4px 4px 0;">
    <p style="color:#58a6ff;font-size:13px;font-weight:600;
              margin:0 0 6px 0;text-transform:uppercase;letter-spacing:1px;">
      Conclusione</p>
    <p style="color:#c9d1d9;font-size:16px;
              line-height:1.7;margin:0;">{takeaway}</p>
  </div>
</div>
"""
        plotly_divs.append(section)

    nav_items = "".join(
        f'<a href="#section-{num}" style="color:#58a6ff;text-decoration:none;'
        f'padding:6px 14px;border:1px solid #30363d;border-radius:20px;'
        f'font-size:15px;white-space:nowrap;">{num}. {title}</a>'
        for num, title in [
            (1, "Regimi"), (2, "Transizioni"), (3, "Correlazione"),
            (4, "CAPE"), (5, "Mean Reversion"), (6, "Cicli"),
        ]
    )

    html = f"""<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Analisi Pattern — US Stocks vs Bonds</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&family=Source+Code+Pro:wght@400;500&display=swap" rel="stylesheet">
<style>
  html, body {{ margin:0; padding:0; background:{PAPER_BG}; color:{TEXT_COL};
               font-family:'Inter', 'Segoe UI', 'Helvetica Neue', sans-serif;
               scroll-behavior:smooth; }}
  .plotly-graph-div {{ width:100%!important; }}
</style>
</head>
<body>

<header style="text-align:center;padding:50px 20px 20px;max-width:900px;margin:0 auto;">
  <h1 style="font-size:clamp(22px,4vw,36px);color:#f0f6fc;margin:0 0 10px;">
    Azioni USA vs Obbligazioni USA<br>Analisi dei Pattern
  </h1>
  <p style="color:{MUTED_COL};font-size:16px;">
    Machine learning e statistica applicati a {TODAY.year - 1910}+ anni di rendimenti annuali
    (dataset Ibbotson, 1910–{TODAY.year})
  </p>
</header>

<nav style="display:flex;gap:8px;justify-content:center;flex-wrap:wrap;
            padding:10px 20px 30px;max-width:900px;margin:0 auto;">
  {nav_items}
  <a href="#caveats" style="color:#f85149;text-decoration:none;
     padding:6px 14px;border:1px solid #f85149;border-radius:20px;
     font-size:15px;white-space:nowrap;">Caveat</a>
</nav>

{"".join(plotly_divs)}

<div id="caveats">
{caveats_html}
</div>

<footer style="text-align:center;padding:30px 20px 50px;max-width:900px;margin:0 auto;">
  <p style="color:{MUTED_COL};font-family:monospace;font-size:11px;">
    Generato il {TODAY} — Dati: Shiller/Yale, FRED, Yahoo Finance —
    <a href="https://github.com/mattia1337/US-Bond-vs-Stock-USA"
       style="color:#58a6ff;">GitHub</a>
  </p>
</footer>

</body>
</html>"""
    return html


# ════════════════════════════════════════════════════════════════════════════
#  MAIN
# ════════════════════════════════════════════════════════════════════════════

def main():
    print("\n" + "=" * 60)
    print("  ANALISI ML — US STOCKS vs US BONDS")
    print("=" * 60)

    # ── fetch dati ──
    _, df_ibbotson = build_datasets()
    df = df_ibbotson[~df_ibbotson["is_partial"]].copy()
    print(f"\n  Dataset: {len(df)} anni completi ({df.year.min()}–{df.year.max()})")

    shiller_ext = None
    try:
        shiller_ext = fetch_shiller_extended()
    except Exception as e:
        print(f"  [AVVISO] Shiller esteso non disponibile: {e}")

    # ── analisi ──
    print("\n  Analisi 1: Regime Clustering (GMM) ...")
    fig1, regime_counts = analysis_regime_clustering(df)

    # aggiorna il takeaway della sezione 1 con i dati dei regimi
    total_years = sum(regime_counts.values())
    gold_n = regime_counts.get("Goldilocks", 0)
    gold_pct = gold_n / total_years * 100
    stag_n = regime_counts.get("Stagflazione / Crisi", 0)
    stag_pct = stag_n / total_years * 100
    # trova il regime più comune e il più raro
    most_common = max(regime_counts, key=regime_counts.get)
    most_common_pct = regime_counts[most_common] / total_years * 100
    least_common = min(regime_counts, key=regime_counts.get)
    least_common_pct = regime_counts[least_common] / total_years * 100
    SECTION_TEXT[1]["takeaway"] = (
        f"Il regime più comune è <b>{most_common}</b>, "
        f"che si verifica nel <b>{most_common_pct:.0f}%</b> degli anni "
        f"({regime_counts[most_common]} su {total_years}). "
        f"Il regime più raro è <b>{least_common}</b> "
        f"(<b>{least_common_pct:.0f}%</b>, {regime_counts[least_common]} anni): "
        f"dove entrambe le asset class perdono valore simultaneamente. "
        f"Il regime <b>Fuga verso la qualità</b> dimostra perché i titoli di Stato "
        f"sono considerati un'assicurazione contro i crolli azionari."
    )

    print("  Analisi 2: Matrice di Transizione Markov ...")
    fig2, trans_data = analysis_markov_transitions(df)

    # aggiorna il takeaway della sezione 2 con i dati di transizione
    probs = trans_data["probs"]
    quad_names = trans_data["quad_names"]
    self_probs = {quad_names[i]: probs[i, i] for i in range(len(quad_names))}
    stickiest = max(self_probs, key=self_probs.get)
    stickiest_pct = self_probs[stickiest]
    crisis_name = "Azioni- Bond-"
    crisis_self = self_probs.get(crisis_name, 0)
    SECTION_TEXT[2]["takeaway"] = (
        f"Le crisi (<b>{crisis_name}</b>) hanno una probabilità di ripetersi "
        f"di solo il <b>{crisis_self:.0f}%</b>: nella maggior parte dei casi, "
        f"l'anno successivo si torna in un quadrante positivo. "
        f"Il quadrante più \"appiccicoso\" è <b>{stickiest}</b> "
        f"(probabilità di restare: <b>{stickiest_pct:.0f}%</b>): "
        f"i periodi buoni tendono a perpetuarsi."
    )

    print("  Analisi 3: Correlazione Rolling ...")
    fig3 = analysis_rolling_correlation(df)

    fig4 = None
    cape_info = None
    if shiller_ext is not None:
        print("  Analisi 4: CAPE come Predittore ...")
        fig4, cape_info = analysis_cape_predictor(df, shiller_ext)

    # aggiorna intro e takeaway della sezione 4 con i dati CAPE
    if cape_info:
        cutoff = cape_info["cutoff_year"]
        example_year = cutoff + 5
        example_future = example_year + 10
        n_indep = cape_info["n_indep"]
        SECTION_TEXT[4]["intro"] = (
            "Il <b>CAPE (Cyclically Adjusted P/E)</b> è un indicatore inventato "
            "dal premio Nobel Robert Shiller. Misura quanto è \"costoso\" il mercato azionario "
            "rispetto ai suoi utili medi degli ultimi 10 anni (aggiustati per l'inflazione).<br><br>"
            "Un CAPE alto significa che stai pagando molto per ogni euro di utili → "
            "storicamente, i rendimenti dei 10 anni successivi tendono ad essere bassi.<br>"
            "Un CAPE basso significa che il mercato è \"a sconto\" → "
            "storicamente, i rendimenti futuri tendono ad essere alti.<br><br>"
            "<b>Perché mancano gli ultimi anni?</b> Questo grafico confronta il CAPE di ogni anno "
            "con il rendimento <b>effettivo</b> dei 10 anni successivi. "
            f"Per esempio, per il {example_year} dovremmo aspettare il {example_future} "
            f"per sapere quanto ha reso il mercato. "
            f"Siccome siamo nel {TODAY.year}, per tutti gli anni dopo il {cutoff} "
            f"non abbiamo ancora 10 anni di dati. "
            "I <span style='color:#f0883e'>&#9670; diamanti arancioni</span> mostrano questi anni recenti, "
            "posizionati sulla linea di regressione (= dove la storia prevede che finiranno).<br><br>"
            "Clicca sulle decadi nella legenda per isolare singoli periodi storici."
        )
        cape_min = cape_info.get("recent_cape_min")
        cape_max = cape_info.get("recent_cape_max")
        cape_range_str = (
            f"{cape_min:.0f}-{cape_max:.0f}" if cape_min is not None else "elevati"
        )
        SECTION_TEXT[4]["takeaway"] = (
            "La relazione è chiara: quando il CAPE è basso (&lt;15), i rendimenti futuri tendono "
            "ad essere elevati. Quando è alto (&gt;25), i rendimenti futuri sono compressi. "
            f"Gli anni recenti hanno CAPE molto alti (<b>{cape_range_str}</b>), "
            f"suggerendo rendimenti futuri modesti — "
            f"ma il verdetto definitivo arriverà solo fra 5-10 anni. "
            f"<b>Attenzione:</b> le finestre di 10 anni si sovrappongono, inflazionando l'R². "
            f"Il campione effettivo di osservazioni indipendenti è ~{n_indep}, non {total_years}+."
        )

    print("  Analisi 5: Mean Reversion ...")
    fig5, prediction = analysis_mean_reversion(df)

    # aggiorna il takeaway della sezione 5 con la previsione concreta
    p = prediction
    bucket = p.get("bucket")
    base_takeaway = (
        "Dopo un crollo, il rendimento mediano dell'anno successivo è <b>sopra la media</b> "
        "(mean reversion). Ma la dispersione è alta: non è una garanzia. "
        "Dopo un boom, i rendimenti successivi restano generalmente positivi "
        "(il momentum tende a persistere nel breve termine)."
    )
    if bucket:
        prediction_text = (
            f"<br><br><span style='color:#f0883e;font-weight:600;'>"
            f"E il {p['next_year']}?</span> "
            f"Il {p['last_year']} ha chiuso a <b>{p['last_return']:+.1f}%</b> "
            f"(categoria: {bucket['label']}). "
            f"Storicamente, dopo anni simili:<br>"
            f"&bull; rendimento mediano anno dopo: <b>{bucket['median']:+.1f}%</b><br>"
            f"&bull; rendimento medio anno dopo: <b>{bucket['mean']:+.1f}%</b><br>"
            f"&bull; probabilità di anno positivo: <b>{bucket['pct_positive']:.0f}%</b><br>"
            f"&bull; range tipico (25°-75° percentile): "
            f"da {bucket['q25']:+.1f}% a {bucket['q75']:+.1f}%<br>"
            f"<i>(Basato su {bucket['n']} precedenti storici — "
            f"non è una previsione, è ciò che dice la storia.)</i>"
        )
        SECTION_TEXT[5]["takeaway"] = base_takeaway + prediction_text
    else:
        SECTION_TEXT[5]["takeaway"] = base_takeaway

    print("  Analisi 6: Autocorrelazione e Cicli ...")
    fig6, acf_info = analysis_autocorrelation(df)

    # aggiorna il takeaway della sezione 6 con i dati ACF reali
    def _describe_acf(label, info):
        sig = info["significant"]
        if not sig:
            return (
                f"Per le <b>{label.lower()}</b>, nessuna barra supera la soglia rossa: "
                f"i rendimenti passati non predicono quelli futuri. "
                f"Coerente con l'ipotesi dei mercati efficienti."
            )
        lag_strs = [f"Lag {lg} ({val:+.3f})" for lg, val in sig]
        neg = [v for _, v in sig if v < 0]
        pos = [v for _, v in sig if v > 0]
        text = (
            f"Per le <b>{label.lower()}</b>, i lag significativi sono: "
            f"{', '.join(lag_strs)}. "
        )
        if neg and not pos:
            text += (
                "Sono tutti negativi, il che suggerisce una tendenza alla "
                "<b>mean reversion</b>: dopo un anno forte, c'è una lieve "
                "tendenza ribassista a distanza di qualche anno."
            )
        elif pos and not neg:
            lags_txt = ", ".join(str(lg) for lg, _ in sig)
            text += (
                f"Sono tutti positivi, il che indica <b>memoria/persistenza</b> "
                f"a {lags_txt} anni: i rendimenti tendono a mantenere la direzione. "
            )
            if label == "Bond":
                text += (
                    "Coerente con i cicli pluriennali dei tassi d'interesse "
                    "(le banche centrali alzano o abbassano i tassi gradualmente)."
                )
        else:
            text += "Un mix di correlazioni positive e negative a diversi lag."
        return text

    acf_takeaway_parts = []
    for label in ["Azioni", "Bond"]:
        if label in acf_info:
            acf_takeaway_parts.append(_describe_acf(label, acf_info[label]))
    SECTION_TEXT[6]["takeaway"] = "<br><br>".join(acf_takeaway_parts)

    # ── assembla HTML ──
    figures = [(1, fig1), (2, fig2), (3, fig3)]
    if fig4 is not None:
        figures.append((4, fig4))
    figures += [(5, fig5), (6, fig6)]

    caveats = build_caveats_html(len(df), int(df.year.min()))
    html = build_html(figures, caveats_html=caveats)
    out = "analysis.html"
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"\n  Salvato: {out}")


if __name__ == "__main__":
    main()
