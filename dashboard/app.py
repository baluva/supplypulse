"""
SupplyPulse — Dashboard BI Supply Chain & Finance (donnees REELLES DataCo).

Lit l'entrepot DuckDB (warehouse.duckdb) construit par le pipeline et restitue
les KPIs logistiques, financiers, geographiques et la qualite des donnees.

Lancement : streamlit run dashboard/app.py
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

import duckdb
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import yaml

# --------------------------------------------------------------------------- #
# Chemins & palette
# --------------------------------------------------------------------------- #
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
DB_PATH = os.path.join(ROOT, "warehouse.duckdb")
REPORT_PATH = os.path.join(ROOT, "governance", "quality_report.json")
DICT_PATH = os.path.join(ROOT, "governance", "data_dictionary.yml")

INK = "#0B1220"
PANEL = "#131D2E"
TEAL = "#2DD4BF"
SKY = "#38BDF8"
CORAL = "#FB7185"
AMBER = "#FBBF24"
GREEN = "#34D399"
VIOLET = "#A78BFA"
TEXT = "#E2E8F0"
MUTED = "#8B9BB4"
GRID = "rgba(139,155,180,0.12)"
SEQ = [TEAL, SKY, AMBER, CORAL, VIOLET, GREEN]

st.set_page_config(page_title="SupplyPulse — Supply Chain Analytics",
                   page_icon="🛰️", layout="wide", initial_sidebar_state="expanded")

# --------------------------------------------------------------------------- #
# CSS
# --------------------------------------------------------------------------- #
st.markdown(
    f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Space+Grotesk:wght@600;700&display=swap');
    html, body, [class*="css"] {{ font-family:'Inter',sans-serif; }}
    .stApp {{ background:
        radial-gradient(1200px 600px at 80% -10%, rgba(45,212,191,0.08), transparent 60%),
        radial-gradient(900px 500px at -10% 10%, rgba(56,189,248,0.07), transparent 55%),
        {INK}; }}
    #MainMenu, footer, header {{ visibility:hidden; }}
    .block-container {{ padding-top:1.6rem; padding-bottom:2rem; max-width:1540px; }}
    .sp-hero {{ display:flex; align-items:center; justify-content:space-between; gap:1rem;
        padding:1.1rem 1.4rem; border-radius:18px;
        background:linear-gradient(135deg, rgba(45,212,191,0.10), rgba(56,189,248,0.04));
        border:1px solid rgba(45,212,191,0.22); margin-bottom:1.1rem; }}
    .sp-title {{ font-family:'Space Grotesk',sans-serif; font-size:1.7rem; font-weight:700;
        color:{TEXT}; margin:0; letter-spacing:-0.5px; }}
    .sp-title span {{ color:{TEAL}; }}
    .sp-sub {{ color:{MUTED}; font-size:0.92rem; margin-top:2px; }}
    .sp-badge {{ background:rgba(52,211,153,0.12); color:{GREEN};
        border:1px solid rgba(52,211,153,0.35); padding:6px 12px; border-radius:999px;
        font-size:0.8rem; font-weight:600; white-space:nowrap; }}
    .kpi-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(170px,1fr));
        gap:14px; margin-bottom:0.4rem; }}
    .kpi {{ background:{PANEL}; border:1px solid rgba(139,155,180,0.14);
        border-left:3px solid {TEAL}; border-radius:14px; padding:16px 18px;
        transition:transform .15s ease, border-color .15s ease; }}
    .kpi:hover {{ transform:translateY(-3px); border-left-color:{SKY}; }}
    .kpi .label {{ color:{MUTED}; font-size:0.76rem; font-weight:600;
        text-transform:uppercase; letter-spacing:0.6px; }}
    .kpi .value {{ color:{TEXT}; font-size:1.8rem; font-weight:700;
        font-family:'Space Grotesk',sans-serif; margin-top:4px; line-height:1.1; }}
    .kpi .sub {{ font-size:0.8rem; margin-top:4px; font-weight:500; }}
    .kpi.good {{ border-left-color:{GREEN}; }}
    .kpi.warn {{ border-left-color:{AMBER}; }}
    .kpi.bad {{ border-left-color:{CORAL}; }}
    .sp-section {{ font-family:'Space Grotesk',sans-serif; font-size:1.1rem; font-weight:600;
        color:{TEXT}; margin:1.1rem 0 0.5rem 0; padding-left:11px; border-left:3px solid {TEAL}; }}
    .sp-insight {{ background:rgba(251,191,36,0.08); border:1px solid rgba(251,191,36,0.3);
        border-radius:12px; padding:12px 16px; color:{TEXT}; font-size:0.9rem; margin:0.4rem 0; }}
    .sp-insight b {{ color:{AMBER}; }}
    .stTabs [data-baseweb="tab-list"] {{ gap:6px; border-bottom:1px solid rgba(139,155,180,0.15); }}
    .stTabs [data-baseweb="tab"] {{ background:transparent; color:{MUTED}; border-radius:10px 10px 0 0;
        padding:9px 16px; font-weight:600; font-size:0.9rem; }}
    .stTabs [aria-selected="true"] {{ background:rgba(45,212,191,0.10); color:{TEAL}; }}
    section[data-testid="stSidebar"] {{ background:{PANEL}; border-right:1px solid rgba(139,155,180,0.12); }}
    section[data-testid="stSidebar"] .sp-side-title {{ font-family:'Space Grotesk',sans-serif;
        color:{TEAL}; font-weight:700; font-size:1.1rem; }}
    .stDataFrame {{ border-radius:12px; overflow:hidden; }}
    </style>
    """, unsafe_allow_html=True)


# --------------------------------------------------------------------------- #
# Bootstrap : construit l'entrepot au 1er lancement (deploiement Streamlit Cloud)
# --------------------------------------------------------------------------- #
@st.cache_resource(show_spinner="Initialisation : téléchargement des données réelles + build de l'entrepôt…")
def ensure_warehouse():
    """Si l'entrepot DuckDB est absent, joue le pipeline complet (idempotent)."""
    if os.path.exists(DB_PATH):
        return True
    csv = os.path.join(ROOT, "data", "dataco", "dataco_supply_chain.csv")
    if not os.path.exists(csv):
        subprocess.run([sys.executable, os.path.join(ROOT, "pipeline", "download_data.py")], check=True)
    subprocess.run([sys.executable, os.path.join(ROOT, "pipeline", "build_warehouse.py")], check=True)
    # Les tests qualite sortent en code 1 si echec : c'est normal, on ne bloque pas l'app.
    subprocess.run([sys.executable, os.path.join(ROOT, "governance", "quality_checks.py")], check=False)
    return True


# --------------------------------------------------------------------------- #
# Chargement (cache)
# --------------------------------------------------------------------------- #
@st.cache_data(show_spinner=False)
def load_fact():
    if not os.path.exists(DB_PATH):
        return None
    con = duckdb.connect(DB_PATH, read_only=True)
    cols = ("order_id, order_item_id, order_month, order_year, days_real, days_scheduled, "
            "delay_days, delivery_status, shipping_mode, late_risk, is_late, is_on_time, "
            "is_canceled, order_status, market, order_region, order_country, customer_segment, "
            "department_name, category_name, sales, profit, profit_ratio, discount_rate, quantity")
    df = con.execute(f"SELECT {cols} FROM fct_sales").fetchdf()
    con.close()
    df["order_month"] = pd.to_datetime(df["order_month"])
    return df


@st.cache_data(show_spinner=False)
def load_catalog_counts():
    con = duckdb.connect(DB_PATH, read_only=True)
    objs = ["dataco_raw", "fct_sales", "mart_monthly_performance", "mart_shipping_mode",
            "mart_category_finance", "mart_region"]
    rows = [{"Objet": o, "Lignes": con.execute(f"SELECT COUNT(*) FROM {o}").fetchone()[0]}
            for o in objs]
    con.close()
    return pd.DataFrame(rows)


@st.cache_data(show_spinner=False)
def load_quality():
    if os.path.exists(REPORT_PATH):
        with open(REPORT_PATH, "r", encoding="utf-8") as fh:
            return json.load(fh)
    return None


@st.cache_data(show_spinner=False)
def load_dictionary():
    if os.path.exists(DICT_PATH):
        with open(DICT_PATH, "r", encoding="utf-8") as fh:
            return yaml.safe_load(fh)
    return None


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def money(x, millions=False):
    if millions:
        return f"{x/1e6:,.1f} M$".replace(",", " ")
    return f"{x:,.0f} $".replace(",", " ")


def num(x):
    return f"{x:,.0f}".replace(",", " ")


def kpi_card(label, value, sub="", tone=""):
    cls = f"kpi {tone}".strip()
    sub_color = {"good": GREEN, "warn": AMBER, "bad": CORAL}.get(tone, MUTED)
    sub_html = f'<div class="sub" style="color:{sub_color}">{sub}</div>' if sub else ""
    return f'<div class="{cls}"><div class="label">{label}</div>' \
           f'<div class="value">{value}</div>{sub_html}</div>'


def style_fig(fig, height=320, legend=True):
    fig.update_layout(
        template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", color=TEXT, size=12),
        margin=dict(l=10, r=10, t=30, b=10), height=height, colorway=SEQ,
        hoverlabel=dict(bgcolor=PANEL, font_size=12, font_family="Inter"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                    bgcolor="rgba(0,0,0,0)") if legend else dict())
    fig.update_xaxes(gridcolor=GRID, zeroline=False, linecolor=GRID)
    fig.update_yaxes(gridcolor=GRID, zeroline=False, linecolor=GRID)
    return fig


def late_rate(df):
    base = df[~df["is_canceled"]]
    return base["is_late"].mean() * 100 if len(base) else 0.0


# --------------------------------------------------------------------------- #
# App
# --------------------------------------------------------------------------- #
ensure_warehouse()
fact = load_fact()
if fact is None:
    st.error("Entrepot introuvable. Lance d'abord :\n\n```\n"
             "python pipeline/download_data.py\npython pipeline/build_warehouse.py\n"
             "python governance/quality_checks.py\n```")
    st.stop()

quality = load_quality()

# ---- Sidebar ---------------------------------------------------------------
with st.sidebar:
    st.markdown('<div class="sp-side-title">🛰️ SupplyPulse</div>', unsafe_allow_html=True)
    st.caption("DataCo Smart Supply Chain · données réelles")

    months = sorted(fact["order_month"].dt.strftime("%Y-%m").unique())
    m_start, m_end = st.select_slider("Période (mois)", options=months,
                                      value=(months[0], months[-1]))
    markets = sorted(fact["market"].dropna().unique())
    sel_markets = st.multiselect("Marché", markets, default=markets)
    modes = sorted(fact["shipping_mode"].dropna().unique())
    sel_modes = st.multiselect("Mode d'expédition", modes, default=modes)
    segments = sorted(fact["customer_segment"].dropna().unique())
    sel_segments = st.multiselect("Segment client", segments, default=segments)

    st.divider()
    late_target = st.slider("Cible taux de retard (%)", 5, 50, 20)
    st.divider()
    if quality:
        st.caption(f"Qualité des données · {quality['quality_score']}%")
        st.caption(f"MAJ pipeline : {quality['generated_at'][:10]}")

# ---- Filtres ---------------------------------------------------------------
mask = (
    (fact["order_month"].dt.strftime("%Y-%m") >= m_start)
    & (fact["order_month"].dt.strftime("%Y-%m") <= m_end)
    & (fact["market"].isin(sel_markets))
    & (fact["shipping_mode"].isin(sel_modes))
    & (fact["customer_segment"].isin(sel_segments))
)
df = fact[mask].copy()
if df.empty:
    st.warning("Aucune commande pour ces filtres.")
    st.stop()

# ---- Header ----------------------------------------------------------------
st.markdown(
    f"""
    <div class="sp-hero">
      <div>
        <p class="sp-title">Supply<span>Pulse</span> — Supply Chain & Sales Analytics</p>
        <div class="sp-sub">DataCo Global · {m_start} → {m_end} ·
        {num(df['order_id'].nunique())} commandes · {num(len(df))} lignes</div>
      </div>
      <div class="sp-badge">● Données réelles · Pipeline DuckDB</div>
    </div>
    """, unsafe_allow_html=True)

# ---- KPIs ------------------------------------------------------------------
lr = late_rate(df)
otr = df[~df["is_canceled"]]["is_on_time"].mean() * 100
delay = df["delay_days"].mean()
sales = df["sales"].sum()
profit = df["profit"].sum()
margin = profit / sales * 100 if sales else 0

lr_tone = "good" if lr <= late_target else ("warn" if lr <= late_target + 15 else "bad")
cards = [
    kpi_card("Taux de retard", f"{lr:.1f}%", f"cible {late_target}% · {lr-late_target:+.1f} pts", lr_tone),
    kpi_card("Livré à l'heure", f"{otr:.1f}%", "à temps + en avance"),
    kpi_card("Écart délai moyen", f"{delay:+.2f} j", "réel − planifié",
             "bad" if delay > 0.5 else "good"),
    kpi_card("Chiffre d'affaires", money(sales, True), "ventes totales"),
    kpi_card("Profit", money(profit, True), f"marge {margin:.1f}%",
             "good" if margin >= 10 else "warn"),
    kpi_card("Panier moyen", money(df.groupby('order_id')['sales'].sum().mean()), "par commande"),
]
st.markdown('<div class="kpi-grid">' + "".join(cards) + "</div>", unsafe_allow_html=True)

tab_over, tab_log, tab_fin, tab_geo, tab_seg, tab_gov = st.tabs(
    ["Vue d'ensemble", "Logistique", "Finance", "Régions & marchés", "Segments", "Gouvernance"])

# ============================== VUE D'ENSEMBLE ============================== #
with tab_over:
    c1, c2 = st.columns([1.5, 1])
    with c1:
        st.markdown('<div class="sp-section">CA & profit mensuels</div>', unsafe_allow_html=True)
        m = df.groupby("order_month").agg(sales=("sales", "sum"), profit=("profit", "sum")).reset_index()
        fig = go.Figure()
        fig.add_bar(x=m["order_month"], y=m["sales"], name="CA", marker_color="rgba(56,189,248,0.45)")
        fig.add_trace(go.Scatter(x=m["order_month"], y=m["profit"], name="Profit",
                                 mode="lines", line=dict(color=TEAL, width=3)))
        st.plotly_chart(style_fig(fig, 330), use_container_width=True)
    with c2:
        st.markdown('<div class="sp-section">Statut de livraison</div>', unsafe_allow_html=True)
        ds = df["delivery_status"].value_counts().reset_index()
        ds.columns = ["status", "n"]
        cmap = {"Late delivery": CORAL, "Advance shipping": GREEN,
                "Shipping on time": TEAL, "Shipping canceled": MUTED}
        fig = px.pie(ds, values="n", names="status", hole=0.58, color="status",
                     color_discrete_map=cmap)
        fig.update_traces(textposition="inside", textinfo="percent")
        st.plotly_chart(style_fig(fig, 330), use_container_width=True)

    c3, c4 = st.columns(2)
    with c3:
        st.markdown('<div class="sp-section">Taux de retard mensuel</div>', unsafe_allow_html=True)
        base = df[~df["is_canceled"]]
        mr = base.groupby("order_month")["is_late"].mean().mul(100).reset_index()
        fig = px.line(mr, x="order_month", y="is_late", markers=True)
        fig.update_traces(line_color=CORAL)
        fig.add_hline(y=late_target, line_dash="dot", line_color=AMBER,
                      annotation_text=f"cible {late_target}%", annotation_font_color=AMBER)
        st.plotly_chart(style_fig(fig, 300, legend=False), use_container_width=True)
    with c4:
        st.markdown('<div class="sp-section">CA par marché</div>', unsafe_allow_html=True)
        mk = df.groupby("market")["sales"].sum().sort_values().reset_index()
        fig = px.bar(mk, x="sales", y="market", orientation="h", text_auto=".2s")
        fig.update_traces(marker_color=TEAL)
        st.plotly_chart(style_fig(fig, 300, legend=False), use_container_width=True)

# ================================= LOGISTIQUE ============================== #
with tab_log:
    st.markdown(
        '<div class="sp-insight">💡 <b>Paradoxe logistique</b> : les modes d\'expédition '
        '« rapides » (First Class, Second Class) sont de loin les plus en retard. '
        'Le SLA promis est irréaliste face au délai réellement tenu.</div>',
        unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="sp-section">Taux de retard par mode d\'expédition</div>',
                    unsafe_allow_html=True)
        base = df[~df["is_canceled"]]
        sm = base.groupby("shipping_mode")["is_late"].mean().mul(100).sort_values().reset_index()
        fig = px.bar(sm, x="is_late", y="shipping_mode", orientation="h", text_auto=".1f")
        fig.update_traces(marker_color=[CORAL if v > 50 else AMBER if v > 20 else GREEN
                                        for v in sm["is_late"]])
        fig.add_vline(x=late_target, line_dash="dot", line_color=SKY)
        st.plotly_chart(style_fig(fig, 300, legend=False), use_container_width=True)
    with c2:
        st.markdown('<div class="sp-section">Délai réel vs planifié (jours)</div>',
                    unsafe_allow_html=True)
        dm = df.groupby("shipping_mode").agg(
            reel=("days_real", "mean"), planifie=("days_scheduled", "mean")).reset_index()
        fig = go.Figure()
        fig.add_bar(x=dm["shipping_mode"], y=dm["planifie"], name="Planifié", marker_color=SKY)
        fig.add_bar(x=dm["shipping_mode"], y=dm["reel"], name="Réel", marker_color=CORAL)
        fig.update_layout(barmode="group")
        st.plotly_chart(style_fig(fig, 300), use_container_width=True)

    c3, c4 = st.columns(2)
    with c3:
        st.markdown('<div class="sp-section">Distribution de l\'écart de délai</div>',
                    unsafe_allow_html=True)
        fig = px.histogram(df, x="delay_days", nbins=20)
        fig.update_traces(marker_color=VIOLET)
        fig.add_vline(x=0, line_dash="dot", line_color=AMBER,
                      annotation_text="0 = à l'heure", annotation_font_color=AMBER)
        st.plotly_chart(style_fig(fig, 300, legend=False), use_container_width=True)
    with c4:
        st.markdown('<div class="sp-section">Taux de retard par région</div>', unsafe_allow_html=True)
        base = df[~df["is_canceled"]]
        rr = base.groupby("order_region")["is_late"].mean().mul(100).sort_values().tail(12).reset_index()
        fig = px.bar(rr, x="is_late", y="order_region", orientation="h", text_auto=".0f")
        fig.update_traces(marker_color=CORAL)
        st.plotly_chart(style_fig(fig, 300, legend=False), use_container_width=True)

# =================================== FINANCE =============================== #
with tab_fin:
    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="sp-section">CA & profit par département</div>', unsafe_allow_html=True)
        dp = df.groupby("department_name").agg(
            sales=("sales", "sum"), profit=("profit", "sum")).sort_values("sales").tail(11).reset_index()
        fig = go.Figure()
        fig.add_bar(y=dp["department_name"], x=dp["sales"], name="CA", orientation="h",
                    marker_color="rgba(56,189,248,0.5)")
        fig.add_bar(y=dp["department_name"], x=dp["profit"], name="Profit", orientation="h",
                    marker_color=TEAL)
        fig.update_layout(barmode="group")
        st.plotly_chart(style_fig(fig, 360), use_container_width=True)
    with c2:
        st.markdown('<div class="sp-section">Marge nette par catégorie (top & flop)</div>',
                    unsafe_allow_html=True)
        cat = df.groupby("category_name").agg(
            sales=("sales", "sum"), profit=("profit", "sum")).reset_index()
        cat = cat[cat["sales"] > cat["sales"].quantile(0.4)]
        cat["margin"] = cat["profit"] / cat["sales"] * 100
        cat = cat.sort_values("margin")
        show = pd.concat([cat.head(6), cat.tail(6)])
        fig = px.bar(show, x="margin", y="category_name", orientation="h", text_auto=".1f")
        fig.update_traces(marker_color=[CORAL if v < 5 else GREEN for v in show["margin"]])
        st.plotly_chart(style_fig(fig, 360, legend=False), use_container_width=True)

    st.markdown('<div class="sp-section">Remise vs marge par catégorie</div>', unsafe_allow_html=True)
    sc = df.groupby("category_name").agg(
        discount=("discount_rate", "mean"), profit=("profit", "sum"),
        sales=("sales", "sum"), units=("quantity", "sum")).reset_index()
    sc["discount"] *= 100
    sc["margin"] = sc["profit"] / sc["sales"] * 100
    sc = sc[sc["sales"] > sc["sales"].quantile(0.3)]
    fig = px.scatter(sc, x="discount", y="margin", size="sales", hover_name="category_name",
                     color="margin", color_continuous_scale=["#CC4B6B", AMBER, GREEN], size_max=40)
    fig.update_layout(xaxis_title="Remise moyenne (%)", yaxis_title="Marge nette (%)")
    fig.add_hline(y=0, line_dash="dot", line_color=MUTED)
    st.plotly_chart(style_fig(fig, 340, legend=False), use_container_width=True)

# ============================== RÉGIONS & MARCHÉS ========================== #
with tab_geo:
    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="sp-section">CA & taux de retard par région</div>',
                    unsafe_allow_html=True)
        base = df[~df["is_canceled"]]
        rg = df.groupby("order_region")["sales"].sum().reset_index()
        lt = base.groupby("order_region")["is_late"].mean().mul(100).reset_index()
        rg = rg.merge(lt, on="order_region").sort_values("sales").tail(12)
        fig = go.Figure()
        fig.add_bar(y=rg["order_region"], x=rg["sales"], orientation="h", name="CA",
                    marker_color=TEAL)
        fig.add_trace(go.Scatter(y=rg["order_region"], x=rg["is_late"], name="Retard %",
                                 mode="markers", marker=dict(color=CORAL, size=10), xaxis="x2"))
        fig = style_fig(fig, 380)
        fig.update_layout(xaxis2=dict(overlaying="x", side="top", title="Retard %",
                                      showgrid=False, range=[0, 100]))
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        st.markdown('<div class="sp-section">Top pays par chiffre d\'affaires</div>',
                    unsafe_allow_html=True)
        co = df.groupby("order_country")["sales"].sum().sort_values().tail(12).reset_index()
        fig = px.bar(co, x="sales", y="order_country", orientation="h", text_auto=".2s")
        fig.update_traces(marker_color=SKY)
        st.plotly_chart(style_fig(fig, 380, legend=False), use_container_width=True)

    st.markdown('<div class="sp-section">Synthèse par marché</div>', unsafe_allow_html=True)
    base = df[~df["is_canceled"]]
    mk = df.groupby("market").agg(orders=("order_id", "nunique"), sales=("sales", "sum"),
                                  profit=("profit", "sum")).reset_index()
    lt = base.groupby("market")["is_late"].mean().mul(100).reset_index()
    mk = mk.merge(lt, on="market")
    mk["margin"] = mk["profit"] / mk["sales"] * 100
    mk = mk.sort_values("sales", ascending=False)
    show = mk.copy()
    show["Commandes"] = show["orders"].map(num)
    show["CA"] = show["sales"].map(lambda x: money(x, True))
    show["Profit"] = show["profit"].map(lambda x: money(x, True))
    show["Marge"] = show["margin"].map(lambda x: f"{x:.1f}%")
    show["Retard"] = show["is_late"].map(lambda x: f"{x:.1f}%")
    st.dataframe(show[["market", "Commandes", "CA", "Profit", "Marge", "Retard"]].rename(
        columns={"market": "Marché"}), hide_index=True, use_container_width=True)

# ================================== SEGMENTS =============================== #
with tab_seg:
    st.markdown('<div class="sp-section">Performance par segment client</div>', unsafe_allow_html=True)
    base = df[~df["is_canceled"]]
    seg = df.groupby("customer_segment").agg(
        orders=("order_id", "nunique"), sales=("sales", "sum"), profit=("profit", "sum")).reset_index()
    lt = base.groupby("customer_segment")["is_late"].mean().mul(100).reset_index()
    seg = seg.merge(lt, on="customer_segment")
    seg["margin"] = seg["profit"] / seg["sales"] * 100
    cols = st.columns(len(seg))
    for col, (_, r) in zip(cols, seg.iterrows()):
        col.markdown(kpi_card(r["customer_segment"], money(r["sales"], True),
                              f"marge {r['margin']:.1f}% · retard {r['is_late']:.0f}%",
                              "good" if r["margin"] >= 10 else "warn"), unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="sp-section">CA mensuel par segment</div>', unsafe_allow_html=True)
        ms = df.groupby(["order_month", "customer_segment"])["sales"].sum().reset_index()
        fig = px.area(ms, x="order_month", y="sales", color="customer_segment")
        st.plotly_chart(style_fig(fig, 320), use_container_width=True)
    with c2:
        st.markdown('<div class="sp-section">Profit par segment & marché</div>', unsafe_allow_html=True)
        sm = df.groupby(["customer_segment", "market"])["profit"].sum().reset_index()
        fig = px.bar(sm, x="customer_segment", y="profit", color="market", barmode="group")
        st.plotly_chart(style_fig(fig, 320), use_container_width=True)

# ================================ GOUVERNANCE ============================== #
with tab_gov:
    if not quality:
        st.info("Rapport qualité absent. Lance : python governance/quality_checks.py")
    else:
        k1, k2, k3, k4 = st.columns(4)
        score = quality["quality_score"]
        k1.markdown(kpi_card("Score qualité", f"{score}%", "tests réussis",
                             "good" if score >= 99 else ("warn" if score >= 90 else "bad")),
                    unsafe_allow_html=True)
        k2.markdown(kpi_card("Tests exécutés", str(quality["total_tests"]),
                             "contrats du dictionnaire"), unsafe_allow_html=True)
        k3.markdown(kpi_card("Tests OK", str(quality["passed"]), "", "good"), unsafe_allow_html=True)
        k4.markdown(kpi_card("Anomalies", str(quality["failed"]), "à investiguer",
                             "bad" if quality["failed"] else "good"), unsafe_allow_html=True)

        c1, c2 = st.columns(2)
        with c1:
            st.markdown('<div class="sp-section">Résultats des tests qualité</div>',
                        unsafe_allow_html=True)
            res = pd.DataFrame(quality["results"])
            res_show = res[["table", "column", "test", "status", "failing_rows"]].rename(
                columns={"table": "Table", "column": "Colonne", "test": "Test",
                         "status": "Statut", "failing_rows": "Lignes KO"})

            def hl(row):
                color = "rgba(251,113,133,0.18)" if row["Statut"] == "FAIL" else ""
                return [f"background-color:{color}"] * len(row)
            st.dataframe(res_show.style.apply(hl, axis=1), hide_index=True,
                         use_container_width=True, height=430)
        with c2:
            st.markdown('<div class="sp-section">Catalogue de l\'entrepôt</div>', unsafe_allow_html=True)
            st.dataframe(load_catalog_counts(), hide_index=True, use_container_width=True)
            catalog = load_dictionary()
            if catalog:
                fct = next((t for t in catalog["tables"] if t["name"] == "fct_sales"), None)
                if fct:
                    st.markdown(
                        f"<div style='color:{MUTED};font-size:0.85rem;margin-top:8px'>"
                        f"<b style='color:{TEXT}'>fct_sales</b> — {fct['description'].strip()}<br>"
                        f"Grain : {fct['grain']} · {len(fct['columns'])} colonnes documentées & testées."
                        "</div>", unsafe_allow_html=True)
            st.markdown(
                f"<div class='sp-insight' style='margin-top:10px'>Le dictionnaire "
                "<code>data_dictionary.yml</code> documente le modèle <b>et</b> déclare les tests "
                "qualité, rejoués à chaque build (exploitable en CI/CD). Ici, 6 301 lignes au "
                "ratio de marge aberrant sont automatiquement signalées.</div>",
                unsafe_allow_html=True)

st.markdown(
    f"<div style='text-align:center;color:{MUTED};font-size:0.8rem;margin-top:1.5rem'>"
    "SupplyPulse · données réelles DataCo Smart Supply Chain (180 519 lignes) · "
    "Pipeline DuckDB (SQL compatible BigQuery) → Staging → Marts → Dashboard</div>",
    unsafe_allow_html=True)
