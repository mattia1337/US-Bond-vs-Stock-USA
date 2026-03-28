# US Stocks vs US Bonds — Annual Returns

Interactive scatter-plot visualizations of **US stock returns vs US bond returns**, year by year, spanning over a century of financial history (1910 -- present).

Each dot on the chart represents a single calendar year. The **X axis** shows the annual stock return (S&P 500) and the **Y axis** shows the annual bond return (US government bonds). Dots are color-coded by decade, and a dashed diagonal line marks the `stocks = bonds` boundary: points above the line are years where bonds outperformed stocks, points below are years where stocks won.

The repository contains three separate implementations of this visualization, built with two different methodologies and two different technologies.

---

## Output files

### `runtime_gs10.html` — Methodology "GS10"

Generated at runtime by `us_bonds_vs_stocks.py`. All data is downloaded live from public APIs.

| Asset class | Source | Coverage |
|---|---|---|
| **Stocks** | Yahoo Finance `^GSPC` (S&P 500 price return), overwritten by `^SP500TR` (S&P 500 total return including dividends) where available | 1928 -- present |
| **Bonds** | FRED Moody's AAA corporate yield as base, overwritten by FRED GS10 (10-Year US Treasury Constant Maturity yield) from 1954 onward. Yield is converted to total return using a **duration model with modified duration = 8.5 years**, which approximates a 10-year Treasury par bond | 1919 -- present |

This methodology focuses on the **10-year Treasury** as the bond benchmark. The shorter duration (8.5) means bond returns are less volatile -- capital gains and losses from rate changes are more moderate compared to the Ibbotson methodology below.

### `runtime_ibbotson.html` — Methodology "Ibbotson"

Generated at runtime by `us_bonds_vs_stocks.py`. All data is downloaded live from public APIs.

| Asset class | Source | Coverage |
|---|---|---|
| **Stocks** | Shiller/Yale `ie_data.xls` S&P Composite total return (monthly price + dividends, compounded annually), overwritten by Yahoo Finance `^SP500TR` from 1988 onward | 1910 -- present |
| **Bonds** | Shiller/Yale GS10 yield as base, overwritten by FRED GS30 (30-Year US Treasury yield) from 1977 onward. Yield is converted to total return using a **duration model with modified duration = 14 years**, which approximates a long-term 20-30 year government bond (matching the Ibbotson SBBI convention) | 1910 -- present |

This methodology mirrors the classic **Ibbotson SBBI (Stocks, Bonds, Bills, and Inflation)** dataset published by Morningstar. The longer duration (14) produces more volatile bond returns -- large capital gains when rates fall, large losses when rates rise. This is the same convention used in most academic finance textbooks.

### `us-bonds-vs-stocks.jsx` — React Component (Static Data)

A standalone React component using [Recharts](https://recharts.org/) with **hardcoded data** from Ibbotson SBBI / Morningstar and Cowles Commission estimates (1910--2024). No runtime data fetching.

Features:
- Interactive hover with custom tooltip showing year, stock return, and bond return
- Decade filter buttons to show/hide individual decades
- Live statistics strip (mean returns, best/worst year, years where both asset classes lost money)
- Dark theme, responsive layout

Data notes for the JSX:
- **1910--1925**: estimates from Cowles Commission / NBER, not official Ibbotson data
- **1926--2024**: Ibbotson SBBI / Morningstar official data
- Stocks = S&P 500 total return (dividends reinvested)
- Bonds = Long-term US Government bonds total return

---

## How the bond duration model works

Since bond yield data is widely available but bond *total return* data is not (especially for historical periods), this project approximates bond total returns from yields using the standard **duration model**:

```
return(t) = yield(t-1) - duration × (yield(t) - yield(t-1))
```

Where:
- `yield(t-1)` is the bond yield at the end of the previous year (the "coupon" income earned)
- `duration × (yield(t) - yield(t-1))` is the approximate capital gain or loss from the change in interest rates
- `duration` is the modified duration of the bond (8.5 for a 10-year Treasury, 14 for a 20-30 year long-term government bond)

When rates **fall**, bondholders earn the coupon *plus* a capital gain. When rates **rise**, the capital loss partially or fully offsets the coupon income.

---

## How to use

### Python script (`us_bonds_vs_stocks.py`)

**Requirements**: Python 3.9+

1. Install dependencies:

```bash
pip install yfinance plotly pandas requests "xlrd==1.2.0" openpyxl numpy
```

2. Run the script:

```bash
python us_bonds_vs_stocks.py
```

3. The script will:
   - Download all data at runtime from Shiller/Yale, FRED, and Yahoo Finance
   - Print diagnostic output showing coverage and statistics for each data source
   - Generate two HTML files in the current directory: `runtime_gs10.html` and `runtime_ibbotson.html`

4. Open the HTML files in any browser. The charts are fully interactive (powered by [Plotly](https://plotly.com/)) -- hover over any dot to see the year and exact returns, click legend entries to toggle decades on/off.

### React component (`us-bonds-vs-stocks.jsx`)

The JSX file is a self-contained React component designed to be dropped into any React project that uses Recharts:

```bash
npm install recharts
```

Then import and render the component:

```jsx
import App from "./us-bonds-vs-stocks";

// Render <App /> in your React app
```

No data fetching is needed -- the dataset is embedded directly in the file.

---

## Data sources

| Source | URL | What it provides |
|---|---|---|
| **Robert Shiller / Yale** | http://www.econ.yale.edu/~shiller/data/ie_data.xls | S&P Composite monthly prices, dividends, and GS10 yield (1871--present) |
| **FRED GS10** | https://fred.stlouisfed.org/series/GS10 | 10-Year Treasury Constant Maturity Rate, monthly (1953--present) |
| **FRED GS30** | https://fred.stlouisfed.org/series/GS30 | 30-Year Treasury Constant Maturity Rate, monthly (1977--present) |
| **FRED AAA** | https://fred.stlouisfed.org/series/AAA | Moody's Seasoned Aaa Corporate Bond Yield, monthly (1919--present) |
| **Yahoo Finance** | `^SP500TR` / `^GSPC` via [yfinance](https://github.com/ranaroussi/yfinance) | S&P 500 Total Return Index (1988--present) and S&P 500 Price Index (1927--present) |

---

## License

This project is licensed under the [GNU General Public License v3.0](LICENSE).
