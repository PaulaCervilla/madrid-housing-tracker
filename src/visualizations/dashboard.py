"""Build an interactive HTML dashboard for the Madrid housing tracker.

The dashboard ships as a single self-contained HTML file with multiple
Plotly charts and a small JS-powered affordability calculator that lets the
user tweak the inputs (dwelling size, savings rate, down-payment ratio) and
see the recomputed years-to-buy in real time.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio

import config

log = logging.getLogger(__name__)


# ---- Theme -----------------------------------------------------------------

BRAND_PRIMARY = "#c0392b"      # tile-roof red, very Madrid
BRAND_ACCENT  = "#2c3e50"      # slate
BRAND_GOLD    = "#d4ac0d"
BRAND_TEAL    = "#117a65"
PALETTE = ["#c0392b", "#2c3e50", "#117a65", "#d4ac0d",
           "#7d3c98", "#2874a6", "#cb4335", "#1e8449"]

_FONT = dict(family="Inter, -apple-system, 'Segoe UI', Roboto, sans-serif",
             size=13, color="#2a2a3c")

pio.templates["madrid"] = go.layout.Template(
    layout=go.Layout(
        font=_FONT,
        title=dict(font=dict(size=16, color="#1a1a2e", family=_FONT["family"]),
                   x=0.02, xanchor="left", y=0.96),
        colorway=PALETTE,
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(l=55, r=20, t=50, b=50),
        xaxis=dict(showgrid=True, gridcolor="#eef0f4", zeroline=False,
                   linecolor="#cfd2da", ticks="outside", tickcolor="#cfd2da"),
        yaxis=dict(showgrid=True, gridcolor="#eef0f4", zeroline=False,
                   linecolor="#cfd2da", ticks="outside", tickcolor="#cfd2da"),
        legend=dict(bgcolor="rgba(255,255,255,0.9)", bordercolor="#e3e5ec",
                    borderwidth=1, font=dict(size=12)),
        hoverlabel=dict(bgcolor="white", bordercolor="#cfd2da",
                        font=dict(size=12, family=_FONT["family"])),
    )
)
pio.templates.default = "madrid"


# ---- Charts ---------------------------------------------------------------


def chart_price_vs_rent_index(aff: pd.DataFrame) -> go.Figure:
    """Both indices on the same chart, rebased to 100 at the first year shown."""
    df = aff.dropna(subset=["hpi"]).copy()
    if df.empty:
        return go.Figure().update_layout(title="No data")

    base_year = df["year"].min()
    base_hpi = df.loc[df["year"] == base_year, "hpi"].iloc[0]
    df["hpi_rebased"] = df["hpi"] / base_hpi * 100

    if df["rpi"].notna().any():
        first_rpi_year = df.loc[df["rpi"].notna(), "year"].min()
        base_rpi = df.loc[df["year"] == first_rpi_year, "rpi"].iloc[0]
        df["rpi_rebased"] = df["rpi"] / base_rpi * 100
    else:
        df["rpi_rebased"] = None

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["year"], y=df["hpi_rebased"],
        name="Precio de compra", mode="lines+markers",
        line=dict(color=BRAND_PRIMARY, width=3),
        marker=dict(size=7),
        hovertemplate="<b>%{x}</b><br>Compra: %{y:.1f}<extra></extra>",
    ))
    if df["rpi_rebased"].notna().any():
        fig.add_trace(go.Scatter(
            x=df["year"], y=df["rpi_rebased"],
            name="Alquiler", mode="lines+markers",
            line=dict(color=BRAND_TEAL, width=3, dash="dash"),
            marker=dict(size=7),
            hovertemplate="<b>%{x}</b><br>Alquiler: %{y:.1f}<extra></extra>",
        ))

    fig.update_layout(
        height=420,
        yaxis_title=f"Índice (base {base_year} = 100)",
        xaxis_title="",
        legend=dict(orientation="h", y=-0.18, x=0.5, xanchor="center"),
    )
    return fig


def chart_absolute_prices(aff: pd.DataFrame) -> go.Figure:
    """Absolute €/m² for purchase and €/m²/mes for rent on dual axis."""
    df = aff.dropna(subset=["price_per_m2"]).copy()
    if df.empty:
        return go.Figure().update_layout(title="No data")

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["year"], y=df["price_per_m2"],
        name="Compra (€/m²)", mode="lines+markers",
        line=dict(color=BRAND_PRIMARY, width=3),
        yaxis="y1",
        hovertemplate="<b>%{x}</b><br>%{y:,.0f} €/m²<extra></extra>",
    ))
    if df["rent_per_m2_month"].notna().any():
        fig.add_trace(go.Scatter(
            x=df["year"], y=df["rent_per_m2_month"],
            name="Alquiler (€/m²/mes)", mode="lines+markers",
            line=dict(color=BRAND_TEAL, width=3, dash="dash"),
            yaxis="y2",
            hovertemplate="<b>%{x}</b><br>%{y:,.1f} €/m²/mes<extra></extra>",
        ))

    fig.update_layout(
        height=420,
        yaxis=dict(title=dict(text="Compra (€/m²)",
                              font=dict(color=BRAND_PRIMARY))),
        yaxis2=dict(title=dict(text="Alquiler (€/m²/mes)",
                               font=dict(color=BRAND_TEAL)),
                    overlaying="y", side="right", showgrid=False),
        legend=dict(orientation="h", y=-0.18, x=0.5, xanchor="center"),
        margin=dict(l=60, r=60, t=30, b=60),
    )
    return fig


def chart_price_to_income(aff: pd.DataFrame) -> go.Figure:
    df = aff.dropna(subset=["price_to_income"]).copy()
    if df.empty:
        return go.Figure().update_layout(title="No data")

    fig = px.bar(
        df, x="year", y="price_to_income",
        color="price_to_income",
        color_continuous_scale=[(0, "#117a65"), (0.5, "#d4ac0d"), (1, "#c0392b")],
        labels={"price_to_income": "Precio / Salario bruto anual",
                "year": ""},
    )
    fig.update_traces(
        hovertemplate="<b>%{x}</b><br>%{y:.1f}× el salario anual<extra></extra>",
        marker_line_width=0,
    )
    fig.update_layout(
        height=380, coloraxis_showscale=False,
        yaxis_title="Veces el salario bruto anual",
    )
    return fig


def chart_years_to_save(aff: pd.DataFrame) -> go.Figure:
    df = aff.dropna(subset=["years_to_down_payment"]).copy()
    if df.empty:
        return go.Figure().update_layout(title="No data")

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["year"], y=df["years_to_down_payment"],
        name="Años para la entrada (20%)",
        mode="lines+markers", line=dict(color=BRAND_PRIMARY, width=3),
        fill="tozeroy", fillcolor="rgba(192, 57, 43, 0.12)",
        hovertemplate="<b>%{x}</b><br>%{y:.1f} años<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=df["year"], y=df["years_to_full_purchase"],
        name="Años para comprar al contado",
        mode="lines+markers", line=dict(color=BRAND_ACCENT, width=2, dash="dot"),
        hovertemplate="<b>%{x}</b><br>%{y:.1f} años<extra></extra>",
    ))
    fig.update_layout(
        height=400, yaxis_title="Años de ahorro necesarios",
        legend=dict(orientation="h", y=-0.18, x=0.5, xanchor="center"),
    )
    return fig


def chart_rent_burden(aff: pd.DataFrame) -> go.Figure:
    df = aff.dropna(subset=["rent_burden"]).copy()
    if df.empty:
        return go.Figure().update_layout(title="No data")

    df["rent_burden_pct"] = df["rent_burden"] * 100
    fig = px.area(
        df, x="year", y="rent_burden_pct",
        labels={"rent_burden_pct": "% del salario bruto anual", "year": ""},
        color_discrete_sequence=[BRAND_TEAL],
    )
    fig.add_hline(
        y=30, line=dict(color=BRAND_PRIMARY, width=1.5, dash="dash"),
        annotation_text="Umbral 30% (sobreesfuerzo)",
        annotation_position="top left",
        annotation_font=dict(color=BRAND_PRIMARY, size=11),
    )
    fig.update_traces(line=dict(width=3),
                      hovertemplate="<b>%{x}</b><br>%{y:.1f}%<extra></extra>")
    fig.update_layout(height=380)
    return fig


# ---- KPIs -----------------------------------------------------------------


def _kpis(aff: pd.DataFrame) -> list[dict]:
    if aff.empty:
        return []
    latest = aff.dropna(subset=["price_per_m2"]).iloc[-1]
    first  = aff.dropna(subset=["price_per_m2"]).iloc[0]
    pct = (latest["price_per_m2"] / first["price_per_m2"] - 1) * 100

    return [
        {"label": "Precio medio (€/m²)",
         "value": f"{latest['price_per_m2']:,.0f} €",
         "sub": f"Madrid · {int(latest['year'])}"},
        {"label": "Variación desde el inicio",
         "value": f"{pct:+.1f}%",
         "sub": f"vs. {int(first['year'])}"},
        {"label": "Precio / Salario anual",
         "value": f"{latest['price_to_income']:.1f}×",
         "sub": "ratio sobre salario bruto"},
        {"label": "Años de ahorro (entrada)",
         "value": f"{latest['years_to_down_payment']:.1f}",
         "sub": "20% entrada · ahorro 20% del neto"},
    ]


# ---- HTML assembly --------------------------------------------------------


CSS = """
:root {
  --brand: #c0392b;
  --brand-dark: #922b21;
  --ink: #1a1a2e;
  --muted: #6b7280;
  --bg: #f7f5f2;
  --card: #ffffff;
  --border: #e6e3dd;
}
* { box-sizing: border-box; }
body {
  font-family: Inter, -apple-system, "Segoe UI", Roboto, sans-serif;
  background: var(--bg); color: var(--ink); margin: 0;
}
.wrap { max-width: 1200px; margin: 0 auto; padding: 32px 24px 64px; }
header h1 { margin: 0; font-size: 32px; letter-spacing: -0.02em; }
header p  { color: var(--muted); margin: 6px 0 0; max-width: 720px; }
.kpis {
  display: grid; gap: 14px;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  margin: 28px 0;
}
.kpi {
  background: var(--card); border: 1px solid var(--border); border-radius: 14px;
  padding: 16px 18px;
}
.kpi .label { font-size: 12px; color: var(--muted); text-transform: uppercase;
              letter-spacing: 0.05em; }
.kpi .value { font-size: 28px; font-weight: 700; color: var(--brand);
              margin-top: 4px; }
.kpi .sub   { font-size: 12px; color: var(--muted); margin-top: 2px; }
.card {
  background: var(--card); border: 1px solid var(--border); border-radius: 14px;
  padding: 18px 18px 8px; margin-bottom: 22px;
}
.card h2 { margin: 0 0 8px; font-size: 18px; }
.card p.lede { color: var(--muted); margin: 0 0 12px; font-size: 13px; }
.grid-2 { display: grid; gap: 22px; grid-template-columns: 1fr; }
@media (min-width: 900px) { .grid-2 { grid-template-columns: 1fr 1fr; } }

/* Calculator */
.calc { display: grid; gap: 16px;
        grid-template-columns: 1fr; align-items: start; }
@media (min-width: 800px) { .calc { grid-template-columns: 320px 1fr; } }
.controls label { display: block; font-size: 13px; color: var(--muted);
                  margin-bottom: 4px; }
.controls .row { margin-bottom: 14px; }
.controls input[type=range] { width: 100%; }
.controls .val { font-weight: 600; color: var(--ink); }
.result {
  background: linear-gradient(135deg, #fff8f6, #fdecea);
  border: 1px solid #f3c4bd; border-radius: 12px; padding: 18px 20px;
}
.result .big { font-size: 42px; font-weight: 800; color: var(--brand);
               line-height: 1; }
.result .label { font-size: 13px; color: var(--muted);
                 text-transform: uppercase; letter-spacing: .05em; }
.result ul { margin: 14px 0 0; padding-left: 18px; color: #333; font-size: 14px; }
.result ul li { margin-bottom: 4px; }

/* Personal calculator (number inputs) */
.pcalc { display: grid; gap: 16px;
         grid-template-columns: 1fr; align-items: start; }
@media (min-width: 800px) { .pcalc { grid-template-columns: 1fr 1fr; } }
.pcalc .inputs { display: grid; gap: 12px;
                 grid-template-columns: 1fr 1fr; }
.pcalc .inputs .full { grid-column: 1 / -1; }
.pcalc label { display: block; font-size: 12px; color: var(--muted);
               text-transform: uppercase; letter-spacing: .05em;
               margin-bottom: 4px; }
.pcalc input[type=number] {
  width: 100%; padding: 10px 12px; font-size: 15px;
  border: 1px solid var(--border); border-radius: 8px;
  background: #fafafa; color: var(--ink);
  font-family: inherit;
}
.pcalc input[type=number]:focus {
  outline: none; border-color: var(--brand);
  background: #fff; box-shadow: 0 0 0 3px rgba(192,57,43,.12);
}
.pcalc .result h3 { margin: 0 0 8px; font-size: 15px; color: var(--ink); }
.pcalc .row-out { display: flex; justify-content: space-between;
                  padding: 6px 0; border-bottom: 1px dashed var(--border);
                  font-size: 14px; }
.pcalc .row-out:last-child { border-bottom: 0; }
.pcalc .row-out b { color: var(--brand); }
.pcalc .verdict { margin-top: 14px; padding: 10px 12px;
                  border-radius: 8px; font-size: 13px; }
.pcalc .verdict.ok   { background: #e8f5e9; color: #1e6b2a; }
.pcalc .verdict.warn { background: #fff4e5; color: #8a5a00; }
.pcalc .verdict.bad  { background: #fdecea; color: #922b21; }

footer {
  background: #1a1a2e; color: #cfd2da;
  text-align: center; padding: 28px 16px; font-size: 13px;
  margin: 40px -24px -64px;  /* break out of .wrap padding */
}
footer a { color: #fff; text-decoration: none;
           border-bottom: 1px dotted #cfd2da; }
footer a:hover { border-bottom-color: #fff; }
footer .stack { margin-top: 8px; opacity: .65; font-size: 11px; }
"""


CALCULATOR_JS_TEMPLATE = """
<script>
const AFF = __AFF_JSON__;
const cfg = {
  netToGross: __NET_TO_GROSS__,
};

function fmtEuro(n) {
  return new Intl.NumberFormat('es-ES', {style:'currency', currency:'EUR',
                                          maximumFractionDigits:0}).format(n);
}
function fmtNum(n, d=1) {
  return new Intl.NumberFormat('es-ES',
    {minimumFractionDigits:d, maximumFractionDigits:d}).format(n);
}

function recompute() {
  const year = parseInt(document.getElementById('year').value);
  const size = parseFloat(document.getElementById('size').value);
  const rate = parseFloat(document.getElementById('savings').value) / 100;
  const dp   = parseFloat(document.getElementById('dp').value) / 100;

  document.getElementById('year-val').textContent = year;
  document.getElementById('size-val').textContent = size + ' m²';
  document.getElementById('savings-val').textContent =
    (rate*100).toFixed(0) + '%';
  document.getElementById('dp-val').textContent = (dp*100).toFixed(0) + '%';

  const row = AFF.find(r => r.year === year);
  if (!row) return;

  const price = row.price_per_m2 * size;
  const wage  = row.wage_eur || 0;
  const net   = wage * cfg.netToGross;
  const annualSavings = net * rate;
  const downPayment = price * dp;
  const yearsDP   = annualSavings > 0 ? downPayment / annualSavings : NaN;
  const yearsFull = annualSavings > 0 ? price / annualSavings : NaN;
  const monthlyRent = (row.rent_per_m2_month || 0) * size;
  const rentBurden  = wage > 0 ? (monthlyRent * 12 / wage) * 100 : NaN;

  document.getElementById('out-years').textContent =
    isFinite(yearsDP) ? fmtNum(yearsDP, 1) : '—';
  document.getElementById('out-price').textContent  = fmtEuro(price);
  document.getElementById('out-dp').textContent     = fmtEuro(downPayment);
  document.getElementById('out-savings').textContent= fmtEuro(annualSavings) + ' / año';
  document.getElementById('out-rent').textContent   =
    monthlyRent > 0 ? fmtEuro(monthlyRent) + ' / mes' : '—';
  document.getElementById('out-burden').textContent =
    isFinite(rentBurden) ? fmtNum(rentBurden,1) + '%' : '—';
  document.getElementById('out-full').textContent   =
    isFinite(yearsFull) ? fmtNum(yearsFull,1) + ' años' : '—';
}

document.addEventListener('DOMContentLoaded', () => {
  ['year','size','savings','dp'].forEach(id => {
    document.getElementById(id).addEventListener('input', recompute);
  });
  recompute();
});
</script>
"""


def _kpi_html(kpis: list[dict]) -> str:
    cards = "".join(
        f'<div class="kpi"><div class="label">{k["label"]}</div>'
        f'<div class="value">{k["value"]}</div>'
        f'<div class="sub">{k["sub"]}</div></div>'
        for k in kpis
    )
    return f'<section class="kpis">{cards}</section>'


def _chart_div(fig: go.Figure, div_id: str) -> str:
    return pio.to_html(
        fig, include_plotlyjs=False, full_html=False,
        div_id=div_id, config={"displayModeBar": False, "responsive": True},
    )


def _calculator_html(aff: pd.DataFrame) -> str:
    if aff.empty:
        return ""

    years = sorted(aff["year"].dropna().astype(int).unique().tolist())
    year_min, year_max = years[0], years[-1]

    # Slim payload for JS — only the columns we need.
    payload = (
        aff[["year", "price_per_m2", "rent_per_m2_month", "wage_eur"]]
        .assign(year=lambda d: d["year"].astype(int))
        .where(pd.notna(aff[["year", "price_per_m2",
                              "rent_per_m2_month", "wage_eur"]]), None)
        .to_dict(orient="records")
    )
    payload_json = json.dumps(payload, allow_nan=False, default=lambda x: None)

    js = (CALCULATOR_JS_TEMPLATE
          .replace("__AFF_JSON__", payload_json)
          .replace("__NET_TO_GROSS__", str(config.NET_TO_GROSS_RATIO)))

    return f"""
<section class="card">
  <h2>Calculadora de esfuerzo</h2>
  <p class="lede">¿Cuántos años de ahorro hacen falta para una vivienda en
     Madrid? Ajusta los parámetros y mira cómo cambia el resultado.</p>
  <div class="calc">
    <div class="controls">
      <div class="row">
        <label>Año: <span class="val" id="year-val"></span></label>
        <input type="range" id="year" min="{year_min}" max="{year_max}"
               value="{year_max}" step="1">
      </div>
      <div class="row">
        <label>Tamaño de la vivienda: <span class="val" id="size-val"></span></label>
        <input type="range" id="size" min="40" max="150"
               value="{int(config.DEFAULT_DWELLING_SIZE_M2)}" step="5">
      </div>
      <div class="row">
        <label>% del sueldo neto que ahorras:
               <span class="val" id="savings-val"></span></label>
        <input type="range" id="savings" min="5" max="50"
               value="{int(config.DEFAULT_SAVINGS_RATE*100)}" step="1">
      </div>
      <div class="row">
        <label>% de entrada exigida:
               <span class="val" id="dp-val"></span></label>
        <input type="range" id="dp" min="10" max="50"
               value="{int(config.DEFAULT_DOWN_PAYMENT_RATIO*100)}" step="1">
      </div>
    </div>
    <div class="result">
      <div class="label">Años de ahorro para la entrada</div>
      <div class="big"><span id="out-years">—</span></div>
      <ul>
        <li>Precio de la vivienda: <b id="out-price">—</b></li>
        <li>Entrada necesaria: <b id="out-dp">—</b></li>
        <li>Ahorro anual estimado: <b id="out-savings">—</b></li>
        <li>Alquiler equivalente: <b id="out-rent">—</b>
            (<b id="out-burden">—</b> del sueldo bruto)</li>
        <li>Años para comprar al contado: <b id="out-full">—</b></li>
      </ul>
    </div>
  </div>
</section>
{js}
"""


PERSONAL_CALC_JS = """
<script>
function fmtEuroP(n) {
  if (!isFinite(n)) return '—';
  return new Intl.NumberFormat('es-ES', {style:'currency', currency:'EUR',
                                          maximumFractionDigits:0}).format(n);
}
function fmtNumP(n, d=1) {
  if (!isFinite(n)) return '—';
  return new Intl.NumberFormat('es-ES',
    {minimumFractionDigits:d, maximumFractionDigits:d}).format(n);
}

function recomputePersonal() {
  const grossYear = parseFloat(document.getElementById('p-salary').value) || 0;
  const saved     = parseFloat(document.getElementById('p-saved').value)  || 0;
  const target    = parseFloat(document.getElementById('p-target').value) || 0;
  const rentMonth = parseFloat(document.getElementById('p-rent').value)   || 0;
  const dpPct     = (parseFloat(document.getElementById('p-dp').value) || 20) / 100;
  const savePct   = (parseFloat(document.getElementById('p-save-pct').value) || 20) / 100;

  // Net income approximation: 22% deductions on average for Spain.
  const net = grossYear * 0.78;
  const monthlyNet = net / 12;
  const monthlyExpenses = monthlyNet - rentMonth;
  // What you can actually save = (net income after rent) × savePct.
  // If user already has a rent expense, only the post-rent surplus is savable.
  const annualSavings = Math.max(0, (monthlyExpenses * 12) * savePct);

  const downPayment = target * dpPct;
  const stillNeededDP = Math.max(0, downPayment - saved);
  const yearsToDP = annualSavings > 0 ? stillNeededDP / annualSavings : Infinity;

  const stillNeededFull = Math.max(0, target - saved);
  const yearsToFull = annualSavings > 0 ? stillNeededFull / annualSavings : Infinity;

  const rentBurden = grossYear > 0 ? (rentMonth * 12 / grossYear) * 100 : NaN;
  const priceToIncome = grossYear > 0 ? target / grossYear : NaN;

  document.getElementById('p-out-net').textContent     = fmtEuroP(net) + ' / año';
  document.getElementById('p-out-savings').textContent = fmtEuroP(annualSavings) + ' / año';
  document.getElementById('p-out-dp').textContent      = fmtEuroP(downPayment);
  document.getElementById('p-out-still-dp').textContent = fmtEuroP(stillNeededDP);
  document.getElementById('p-out-years-dp').textContent =
    isFinite(yearsToDP) ? fmtNumP(yearsToDP, 1) + ' años' : '—';
  document.getElementById('p-out-years-full').textContent =
    isFinite(yearsToFull) ? fmtNumP(yearsToFull, 1) + ' años' : '—';
  document.getElementById('p-out-burden').textContent =
    isFinite(rentBurden) ? fmtNumP(rentBurden, 1) + '%' : '—';
  document.getElementById('p-out-pti').textContent =
    isFinite(priceToIncome) ? fmtNumP(priceToIncome, 1) + '×' : '—';

  // Verdict (qualitative).
  const verdict = document.getElementById('p-verdict');
  verdict.classList.remove('ok','warn','bad');
  if (annualSavings <= 0) {
    verdict.textContent = 'Con estos datos no te queda margen de ahorro tras pagar el alquiler.';
    verdict.classList.add('bad');
  } else if (yearsToDP <= 5) {
    verdict.textContent = '✅ Objetivo alcanzable: podrías reunir la entrada en menos de 5 años.';
    verdict.classList.add('ok');
  } else if (yearsToDP <= 10) {
    verdict.textContent = '⚠️ Plazo realista pero exigente: entre 5 y 10 años para la entrada.';
    verdict.classList.add('warn');
  } else {
    verdict.textContent = '🚧 Plazo muy largo: más de 10 años para la entrada con este ritmo de ahorro.';
    verdict.classList.add('bad');
  }
}

document.addEventListener('DOMContentLoaded', () => {
  ['p-salary','p-saved','p-target','p-rent','p-dp','p-save-pct'].forEach(id => {
    document.getElementById(id).addEventListener('input', recomputePersonal);
  });
  recomputePersonal();
});
</script>
"""


def _personal_calculator_html() -> str:
    return f"""
<section class="card">
  <h2>Tu situación personal</h2>
  <p class="lede">Introduce tus datos reales para estimar cuánto puedes ahorrar
     al año y en cuántos años podrías comprar la vivienda que te interesa.
     Todo se calcula en tu navegador, no se envía nada.</p>
  <div class="pcalc">
    <div class="inputs">
      <div>
        <label>Sueldo bruto anual (€)</label>
        <input type="number" id="p-salary" min="0" step="1000" value="35000">
      </div>
      <div>
        <label>Ahorrado actualmente (€)</label>
        <input type="number" id="p-saved" min="0" step="1000" value="15000">
      </div>
      <div>
        <label>Precio de la vivienda objetivo (€)</label>
        <input type="number" id="p-target" min="0" step="5000" value="350000">
      </div>
      <div>
        <label>Alquiler actual (€/mes)</label>
        <input type="number" id="p-rent" min="0" step="50" value="900">
      </div>
      <div>
        <label>% de entrada exigida</label>
        <input type="number" id="p-dp" min="0" max="100" step="1"
               value="{int(config.DEFAULT_DOWN_PAYMENT_RATIO*100)}">
      </div>
      <div>
        <label>% del sobrante que ahorras</label>
        <input type="number" id="p-save-pct" min="0" max="100" step="1"
               value="{int(config.DEFAULT_SAVINGS_RATE*100)}">
      </div>
    </div>

    <div class="result">
      <h3>Resultado</h3>
      <div class="row-out"><span>Sueldo neto estimado</span>
                           <b id="p-out-net">—</b></div>
      <div class="row-out"><span>Ahorro disponible al año</span>
                           <b id="p-out-savings">—</b></div>
      <div class="row-out"><span>Entrada necesaria</span>
                           <b id="p-out-dp">—</b></div>
      <div class="row-out"><span>Te falta para la entrada</span>
                           <b id="p-out-still-dp">—</b></div>
      <div class="row-out"><span>Años hasta tener la entrada</span>
                           <b id="p-out-years-dp">—</b></div>
      <div class="row-out"><span>Años para comprar al contado</span>
                           <b id="p-out-years-full">—</b></div>
      <div class="row-out"><span>Carga del alquiler actual</span>
                           <b id="p-out-burden">—</b></div>
      <div class="row-out"><span>Precio / sueldo bruto anual</span>
                           <b id="p-out-pti">—</b></div>
      <div id="p-verdict" class="verdict">—</div>
    </div>
  </div>
</section>
{PERSONAL_CALC_JS}
"""


def build_dashboard(aff: pd.DataFrame) -> Path:
    """Render the dashboard to `output/dashboard.html` and return the path."""
    kpis = _kpis(aff)

    fig_idx     = chart_price_vs_rent_index(aff)
    fig_abs     = chart_absolute_prices(aff)
    fig_pti     = chart_price_to_income(aff)
    fig_years   = chart_years_to_save(aff)
    fig_burden  = chart_rent_burden(aff)

    plotly_cdn = (
        '<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>'
    )

    html = f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Madrid Housing Tracker</title>
{plotly_cdn}
<style>{CSS}</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>Madrid Housing Tracker</h1>
    <p>Cómo han evolucionado los precios de compra y alquiler de la vivienda
       en la Comunidad de Madrid, y cuánto esfuerzo cuesta hoy comprar una
       casa con un sueldo medio. Datos públicos del INE.</p>
  </header>

  {_kpi_html(kpis)}

  <section class="card">
    <h2>Índices de precios — compra vs. alquiler</h2>
    <p class="lede">Ambos índices reescalados a 100 en el primer año
       disponible para ver el ritmo relativo de subida.</p>
    {_chart_div(fig_idx, "fig-idx")}
  </section>

  <div class="grid-2">
    <section class="card">
      <h2>Precio absoluto estimado</h2>
      <p class="lede">€/m² para compra y €/m²/mes para alquiler, anclados a
         los valores medios públicos de Madrid en 2015.</p>
      {_chart_div(fig_abs, "fig-abs")}
    </section>
    <section class="card">
      <h2>Ratio precio / salario</h2>
      <p class="lede">Cuántas veces el salario bruto anual cuesta una vivienda
         media. Por encima de 6× se considera muy poco asequible.</p>
      {_chart_div(fig_pti, "fig-pti")}
    </section>
  </div>

  <div class="grid-2">
    <section class="card">
      <h2>Años de ahorro necesarios</h2>
      <p class="lede">Suponiendo que se ahorra un
         {int(config.DEFAULT_SAVINGS_RATE*100)}% del sueldo neto cada año.</p>
      {_chart_div(fig_years, "fig-years")}
    </section>
    <section class="card">
      <h2>Carga del alquiler sobre el sueldo</h2>
      <p class="lede">% del salario bruto anual destinado al alquiler de una
         vivienda media. El umbral del 30% indica sobreesfuerzo.</p>
      {_chart_div(fig_burden, "fig-burden")}
    </section>
  </div>

  {_calculator_html(aff)}

  {_personal_calculator_html()}

  <footer>
    <div>
      Construido con <strong>Python</strong> · pandas · Plotly ·
      <a href="https://github.com/PaulaCervilla/madrid-housing-tracker"
         target="_blank" rel="noopener">ver código en GitHub</a>
    </div>
    <div class="stack">
      Fuentes: INE (IPV, IPVA, IPC, EAES) · Cálculos propios ·
      cifras absolutas ancladas a precios medios públicos de Madrid 2015.
    </div>
  </footer>
</div>
</body>
</html>
"""

    out = config.OUTPUT_DIR / "dashboard.html"
    out.write_text(html, encoding="utf-8")
    log.info("Dashboard written to %s", out)
    return out
