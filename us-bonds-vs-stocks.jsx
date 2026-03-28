import { useState, useMemo } from "react";
import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
  Label,
} from "recharts";

const RAW_DATA = [
  // 1910s — dati stimati da Cowles Commission / NBER / Ibbotson pre-SBBI
  { year: 1910, stocks: -8.0,  bonds: 3.5  },
  { year: 1911, stocks:  0.0,  bonds: 4.5  },
  { year: 1912, stocks:  7.6,  bonds: 1.8  },
  { year: 1913, stocks: -8.4,  bonds: 3.0  },
  { year: 1914, stocks: -5.4,  bonds: 2.8  },
  { year: 1915, stocks: 81.7,  bonds: 2.4  },
  { year: 1916, stocks:  7.7,  bonds: 1.6  },
  { year: 1917, stocks: -21.7, bonds: -8.2 },
  { year: 1918, stocks:  10.5, bonds: 1.5  },
  { year: 1919, stocks:  30.5, bonds: 5.0  },
  // 1920–1925
  { year: 1920, stocks: -23.1, bonds: 3.8  },
  { year: 1921, stocks:  28.1, bonds: 5.8  },
  { year: 1922, stocks:  42.3, bonds: 3.5  },
  { year: 1923, stocks:   3.2, bonds: 4.5  },
  { year: 1924, stocks:  26.2, bonds: 5.0  },
  { year: 1925, stocks:  24.0, bonds: 4.0  },
  // 1926 in poi — Ibbotson SBBI ufficiale
  { year: 1926, stocks: 11.6, bonds: 7.8 },
  { year: 1927, stocks: 37.5, bonds: 8.9 },
  { year: 1928, stocks: 43.6, bonds: 0.1 },
  { year: 1929, stocks: -8.4, bonds: 3.4 },
  { year: 1930, stocks: -24.9, bonds: 4.7 },
  { year: 1931, stocks: -43.3, bonds: -5.3 },
  { year: 1932, stocks: -8.2, bonds: 16.8 },
  { year: 1933, stocks: 54.0, bonds: -0.1 },
  { year: 1934, stocks: -1.4, bonds: 10.0 },
  { year: 1935, stocks: 47.7, bonds: 5.0 },
  { year: 1936, stocks: 33.9, bonds: 7.5 },
  { year: 1937, stocks: -35.0, bonds: 0.2 },
  { year: 1938, stocks: 31.1, bonds: 5.5 },
  { year: 1939, stocks: -0.4, bonds: 5.9 },
  { year: 1940, stocks: -9.8, bonds: 6.1 },
  { year: 1941, stocks: -11.6, bonds: 0.9 },
  { year: 1942, stocks: 20.3, bonds: 3.2 },
  { year: 1943, stocks: 25.9, bonds: 2.1 },
  { year: 1944, stocks: 19.8, bonds: 2.8 },
  { year: 1945, stocks: 36.4, bonds: 10.7 },
  { year: 1946, stocks: -8.1, bonds: -0.1 },
  { year: 1947, stocks: 5.7, bonds: -2.6 },
  { year: 1948, stocks: 5.5, bonds: 3.4 },
  { year: 1949, stocks: 18.8, bonds: 6.5 },
  { year: 1950, stocks: 31.7, bonds: 0.1 },
  { year: 1951, stocks: 24.0, bonds: -3.9 },
  { year: 1952, stocks: 18.4, bonds: 1.2 },
  { year: 1953, stocks: -1.0, bonds: 3.6 },
  { year: 1954, stocks: 52.6, bonds: 7.2 },
  { year: 1955, stocks: 31.6, bonds: -1.3 },
  { year: 1956, stocks: 6.6, bonds: -5.6 },
  { year: 1957, stocks: -10.8, bonds: 7.5 },
  { year: 1958, stocks: 43.4, bonds: -6.1 },
  { year: 1959, stocks: 12.0, bonds: -2.3 },
  { year: 1960, stocks: 0.5, bonds: 13.8 },
  { year: 1961, stocks: 26.9, bonds: 0.9 },
  { year: 1962, stocks: -8.7, bonds: 6.9 },
  { year: 1963, stocks: 22.8, bonds: 1.2 },
  { year: 1964, stocks: 16.5, bonds: 3.5 },
  { year: 1965, stocks: 12.5, bonds: 0.7 },
  { year: 1966, stocks: -10.1, bonds: 3.7 },
  { year: 1967, stocks: 24.0, bonds: -9.2 },
  { year: 1968, stocks: 11.1, bonds: -0.3 },
  { year: 1969, stocks: -8.5, bonds: -5.1 },
  { year: 1970, stocks: 4.0, bonds: 12.1 },
  { year: 1971, stocks: 14.3, bonds: 13.2 },
  { year: 1972, stocks: 19.0, bonds: 5.7 },
  { year: 1973, stocks: -14.7, bonds: -1.1 },
  { year: 1974, stocks: -26.5, bonds: 4.4 },
  { year: 1975, stocks: 37.2, bonds: 9.2 },
  { year: 1976, stocks: 23.8, bonds: 16.8 },
  { year: 1977, stocks: -7.2, bonds: -0.7 },
  { year: 1978, stocks: 6.6, bonds: -1.2 },
  { year: 1979, stocks: 18.4, bonds: -1.2 },
  { year: 1980, stocks: 32.4, bonds: -4.0 },
  { year: 1981, stocks: -4.9, bonds: 1.9 },
  { year: 1982, stocks: 21.4, bonds: 40.4 },
  { year: 1983, stocks: 22.5, bonds: 0.7 },
  { year: 1984, stocks: 6.3, bonds: 15.5 },
  { year: 1985, stocks: 32.2, bonds: 30.1 },
  { year: 1986, stocks: 18.5, bonds: 24.4 },
  { year: 1987, stocks: 5.2, bonds: -2.7 },
  { year: 1988, stocks: 16.8, bonds: 9.7 },
  { year: 1989, stocks: 31.5, bonds: 18.1 },
  { year: 1990, stocks: -3.2, bonds: 6.2 },
  { year: 1991, stocks: 30.5, bonds: 19.3 },
  { year: 1992, stocks: 7.6, bonds: 8.1 },
  { year: 1993, stocks: 10.1, bonds: 18.2 },
  { year: 1994, stocks: 1.3, bonds: -7.8 },
  { year: 1995, stocks: 37.6, bonds: 31.7 },
  { year: 1996, stocks: 23.0, bonds: -0.9 },
  { year: 1997, stocks: 33.4, bonds: 15.9 },
  { year: 1998, stocks: 28.6, bonds: 13.1 },
  { year: 1999, stocks: 21.0, bonds: -8.3 },
  { year: 2000, stocks: -9.1, bonds: 21.5 },
  { year: 2001, stocks: -11.9, bonds: 3.7 },
  { year: 2002, stocks: -22.1, bonds: 17.8 },
  { year: 2003, stocks: 28.7, bonds: 1.5 },
  { year: 2004, stocks: 10.9, bonds: 8.5 },
  { year: 2005, stocks: 4.9, bonds: 2.9 },
  { year: 2006, stocks: 15.8, bonds: 1.0 },
  { year: 2007, stocks: 5.5, bonds: 10.2 },
  { year: 2008, stocks: -37.0, bonds: 25.9 },
  { year: 2009, stocks: 26.5, bonds: -14.9 },
  { year: 2010, stocks: 15.1, bonds: 10.1 },
  { year: 2011, stocks: 2.1, bonds: 29.9 },
  { year: 2012, stocks: 16.0, bonds: 3.6 },
  { year: 2013, stocks: 32.4, bonds: -13.3 },
  { year: 2014, stocks: 13.7, bonds: 27.2 },
  { year: 2015, stocks: 1.4, bonds: -1.2 },
  { year: 2016, stocks: 12.0, bonds: 1.0 },
  { year: 2017, stocks: 21.8, bonds: 8.7 },
  { year: 2018, stocks: -4.4, bonds: 0.0 },
  { year: 2019, stocks: 31.5, bonds: 25.0 },
  { year: 2020, stocks: 18.4, bonds: 11.3 },
  { year: 2021, stocks: 28.7, bonds: -4.4 },
  { year: 2022, stocks: -18.1, bonds: -17.8 },
  { year: 2023, stocks: 26.3, bonds: -3.5 },
  { year: 2024, stocks: 25.0, bonds: 1.0 },
];

const DECADE_COLORS = {
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
};

const getDecade = (year) => {
  const d = Math.floor(year / 10) * 10;
  return `${d}s`;
};

const CustomDot = (props) => {
  const { cx, cy, payload, hoveredYear, setHoveredYear } = props;
  const decade = getDecade(payload.year);
  const color = DECADE_COLORS[decade] || "#aaa";
  const isHovered = hoveredYear === payload.year;
  const shortYear = String(payload.year).slice(2);
  return (
    <g
      style={{ cursor: "pointer" }}
      onMouseEnter={() => setHoveredYear(payload.year)}
      onMouseLeave={() => setHoveredYear(null)}
    >
      <circle
        cx={cx}
        cy={cy}
        r={isHovered ? 9 : 6}
        fill={color}
        fillOpacity={isHovered ? 1 : 0.82}
        stroke={isHovered ? "#fff" : "#0d1117"}
        strokeWidth={isHovered ? 1.5 : 0.8}
        style={{ transition: "r 0.1s" }}
      />
      <text
        x={cx}
        y={cy + 4}
        textAnchor="middle"
        fontSize={isHovered ? 8 : 6.5}
        fontWeight={isHovered ? 700 : 500}
        fontFamily="'DM Mono', monospace"
        fill={isHovered ? "#0d1117" : "#0d1117"}
        style={{ pointerEvents: "none", userSelect: "none" }}
      >
        {shortYear}
      </text>
    </g>
  );
};

const CustomTooltip = ({ active, payload }) => {
  if (!active || !payload || !payload.length) return null;
  const d = payload[0].payload;
  const decade = getDecade(d.year);
  const color = DECADE_COLORS[decade];
  return (
    <div style={{
      background: "#0d1117",
      border: `1px solid ${color}`,
      borderRadius: 2,
      padding: "10px 14px",
      fontFamily: "'DM Mono', monospace",
      fontSize: 12,
      color: "#e6edf3",
      boxShadow: `0 0 16px ${color}40`,
    }}>
      <div style={{ color, fontWeight: 700, fontSize: 14, marginBottom: 6, letterSpacing: 1 }}>
        {d.year}
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
        <span>
          <span style={{ color: "#8b949e" }}>Stocks (S&P)  </span>
          <span style={{ color: d.stocks >= 0 ? "#3fb950" : "#f85149", fontWeight: 600 }}>
            {d.stocks >= 0 ? "+" : ""}{d.stocks.toFixed(1)}%
          </span>
        </span>
        <span>
          <span style={{ color: "#8b949e" }}>Bonds (LT Gov) </span>
          <span style={{ color: d.bonds >= 0 ? "#3fb950" : "#f85149", fontWeight: 600 }}>
            {d.bonds >= 0 ? "+" : ""}{d.bonds.toFixed(1)}%
          </span>
        </span>
      </div>
    </div>
  );
};

export default function App() {
  const [hoveredYear, setHoveredYear] = useState(null);
  const [selectedDecades, setSelectedDecades] = useState(new Set(Object.keys(DECADE_COLORS)));

  const filteredData = useMemo(
    () => RAW_DATA.filter((d) => selectedDecades.has(getDecade(d.year))),
    [selectedDecades]
  );

  const toggleDecade = (decade) => {
    setSelectedDecades((prev) => {
      const next = new Set(prev);
      if (next.has(decade)) {
        if (next.size > 1) next.delete(decade);
      } else {
        next.add(decade);
      }
      return next;
    });
  };

  const toggleAll = () => {
    if (selectedDecades.size === Object.keys(DECADE_COLORS).length) {
      setSelectedDecades(new Set([Object.keys(DECADE_COLORS)[0]]));
    } else {
      setSelectedDecades(new Set(Object.keys(DECADE_COLORS)));
    }
  };

  return (
    <div style={{
      background: "#0d1117",
      minHeight: "100vh",
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      padding: "36px 24px",
      fontFamily: "'DM Mono', 'Courier New', monospace",
      color: "#e6edf3",
    }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@300;400;500&family=Playfair+Display:wght@700;900&display=swap');
        * { box-sizing: border-box; }
        .decade-btn { transition: all 0.15s ease; }
        .decade-btn:hover { transform: translateY(-1px); }
      `}</style>

      {/* Header */}
      <div style={{ textAlign: "center", marginBottom: 32, maxWidth: 740 }}>
        <div style={{
          fontSize: 11,
          letterSpacing: 4,
          color: "#8b949e",
          textTransform: "uppercase",
          marginBottom: 10,
        }}>
          Annual Returns 1910 – 2024
        </div>
        <h1 style={{
          fontFamily: "'Playfair Display', Georgia, serif",
          fontSize: "clamp(22px, 4vw, 38px)",
          fontWeight: 900,
          margin: 0,
          lineHeight: 1.15,
          letterSpacing: -0.5,
          color: "#f0f6fc",
        }}>
          US Stocks<span style={{ color: "#c9b037" }}> vs </span>US Bonds
        </h1>
        <p style={{
          color: "#8b949e",
          fontSize: 12,
          marginTop: 10,
          lineHeight: 1.6,
          letterSpacing: 0.2,
        }}>
          Ogni punto rappresenta un anno. Asse X = rendimento annuo dell'S&P 500 (total return).
          Asse Y = rendimento annuo dei Bond governativi a lungo termine. Fonte: Ibbotson / Morningstar SBBI.
        </p>
      </div>

      {/* Decade filter */}
      <div style={{
        display: "flex",
        flexWrap: "wrap",
        gap: 8,
        justifyContent: "center",
        marginBottom: 28,
        maxWidth: 760,
      }}>
        <button
          className="decade-btn"
          onClick={toggleAll}
          style={{
            background: selectedDecades.size === Object.keys(DECADE_COLORS).length ? "#21262d" : "#161b22",
            border: "1px solid #30363d",
            color: "#e6edf3",
            borderRadius: 2,
            padding: "4px 12px",
            fontSize: 11,
            letterSpacing: 1.5,
            cursor: "pointer",
            textTransform: "uppercase",
          }}
        >
          {selectedDecades.size === Object.keys(DECADE_COLORS).length ? "Deselect all" : "Select all"}
        </button>
        {Object.entries(DECADE_COLORS).map(([decade, color]) => {
          const active = selectedDecades.has(decade);
          return (
            <button
              key={decade}
              className="decade-btn"
              onClick={() => toggleDecade(decade)}
              style={{
                background: active ? `${color}22` : "#161b22",
                border: `1px solid ${active ? color : "#30363d"}`,
                color: active ? color : "#484f58",
                borderRadius: 2,
                padding: "4px 12px",
                fontSize: 11,
                letterSpacing: 1,
                cursor: "pointer",
                fontFamily: "'DM Mono', monospace",
              }}
            >
              {decade}
            </button>
          );
        })}
      </div>

      {/* Chart */}
      <div style={{
        width: "100%",
        maxWidth: 820,
        background: "#161b22",
        border: "1px solid #21262d",
        borderRadius: 4,
        padding: "28px 12px 20px 4px",
      }}>
        <ResponsiveContainer width="100%" height={520}>
          <ScatterChart margin={{ top: 20, right: 30, bottom: 50, left: 30 }}>
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="#21262d"
              horizontal={true}
              vertical={true}
            />
            <XAxis
              type="number"
              dataKey="stocks"
              domain={[-50, 90]}
              tickCount={12}
              tick={{ fill: "#8b949e", fontSize: 11, fontFamily: "'DM Mono', monospace" }}
              tickLine={{ stroke: "#30363d" }}
              axisLine={{ stroke: "#30363d" }}
            >
              <Label
                value="Stock Return (%)"
                position="insideBottom"
                offset={-36}
                style={{ fill: "#8b949e", fontSize: 11, fontFamily: "'DM Mono', monospace", letterSpacing: 1 }}
              />
            </XAxis>
            <YAxis
              type="number"
              dataKey="bonds"
              domain={[-20, 45]}
              tickCount={14}
              tick={{ fill: "#8b949e", fontSize: 11, fontFamily: "'DM Mono', monospace" }}
              tickLine={{ stroke: "#30363d" }}
              axisLine={{ stroke: "#30363d" }}
            >
              <Label
                value="Bond Return (%)"
                angle={-90}
                position="insideLeft"
                offset={-14}
                style={{ fill: "#8b949e", fontSize: 11, fontFamily: "'DM Mono', monospace", letterSpacing: 1 }}
              />
            </YAxis>

            {/* Zero reference lines */}
            <ReferenceLine x={0} stroke="#30363d" strokeDasharray="4 4" strokeWidth={1} />
            <ReferenceLine y={0} stroke="#30363d" strokeDasharray="4 4" strokeWidth={1} />

            {/* Diagonal: bonds = stocks */}
            <ReferenceLine
              segment={[{ x: -50, y: -50 }, { x: 90, y: 90 }]}
              stroke="#c9b037"
              strokeDasharray="6 4"
              strokeOpacity={0.25}
              strokeWidth={1}
            />

            <Tooltip content={<CustomTooltip />} />

            <Scatter
              data={filteredData}
              shape={(props) => (
                <CustomDot
                  {...props}
                  hoveredYear={hoveredYear}
                  setHoveredYear={setHoveredYear}
                />
              )}
            />
          </ScatterChart>
        </ResponsiveContainer>
      </div>

      {/* Stats strip */}
      <div style={{
        display: "flex",
        flexWrap: "wrap",
        gap: 1,
        marginTop: 20,
        maxWidth: 820,
        width: "100%",
      }}>
        {[
          {
            label: "Anni analizzati",
            value: filteredData.length,
            unit: "",
          },
          {
            label: "Media Stocks",
            value: (filteredData.reduce((a, d) => a + d.stocks, 0) / (filteredData.length || 1)).toFixed(1),
            unit: "%",
            color: "#3fb950",
          },
          {
            label: "Media Bonds",
            value: (filteredData.reduce((a, d) => a + d.bonds, 0) / (filteredData.length || 1)).toFixed(1),
            unit: "%",
            color: "#58a6ff",
          },
          {
            label: "Peggiore anno Stocks",
            value: filteredData.length ? Math.min(...filteredData.map((d) => d.stocks)).toFixed(1) : "--",
            unit: "%",
            color: "#f85149",
          },
          {
            label: "Migliore anno Stocks",
            value: filteredData.length ? Math.max(...filteredData.map((d) => d.stocks)).toFixed(1) : "--",
            unit: "%",
            color: "#3fb950",
          },
          {
            label: "Anni entrambi negativi",
            value: filteredData.filter((d) => d.stocks < 0 && d.bonds < 0).length,
            unit: "",
            color: "#f85149",
          },
        ].map((stat, i) => (
          <div
            key={i}
            style={{
              flex: "1 1 130px",
              background: "#161b22",
              border: "1px solid #21262d",
              padding: "12px 16px",
              textAlign: "center",
            }}
          >
            <div style={{
              fontSize: 10,
              color: "#484f58",
              letterSpacing: 1.2,
              textTransform: "uppercase",
              marginBottom: 6,
            }}>
              {stat.label}
            </div>
            <div style={{
              fontSize: 22,
              fontWeight: 500,
              color: stat.color || "#c9b037",
              letterSpacing: -0.5,
            }}>
              {stat.value}{stat.unit}
            </div>
          </div>
        ))}
      </div>

      <div style={{
        marginTop: 18,
        fontSize: 10,
        color: "#484f58",
        letterSpacing: 0.8,
        textAlign: "center",
        maxWidth: 700,
        lineHeight: 1.7,
      }}>
        Stocks = S&P 500 / Cowles Commission index total return. Bonds = Long-term US Government bonds.
        1910–1925: stime da Cowles Commission / NBER, non ufficiali Ibbotson. 1926+: Ibbotson SBBI / Morningstar.
        La linea diagonale tratteggiata gialla rappresenta la parità stock=bond (y=x).
      </div>
    </div>
  );
}
