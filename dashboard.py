"""
Cash income dashboard (prototype).
Run: streamlit run dashboard.py
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from load_report import DEFAULT_REPORT, KNOWN_LINES, load_turnover

ACCENT = "#0F766E"
MUTED = "#64748B"
FONT = "Segoe UI, system-ui, sans-serif"

CHART_TYPES = {
    "Столбчатая (стек)": {"kind": "bar", "barmode": "stack"},
    "Столбчатая (группы)": {"kind": "bar", "barmode": "group"},
    "Линейная": {"kind": "line", "barmode": None},
    "Область (стек)": {"kind": "area", "barmode": None},
}


def inject_styles() -> None:
    st.markdown(
        f"""
        <style>
        .stApp {{
            background: #ffffff;
        }}
        h1 {{
            font-family: {FONT};
            font-weight: 700;
            color: #0f172a;
            letter-spacing: -0.02em;
        }}
        [data-testid="stSidebar"] {{
            background: #f8fafc;
            border-right: 1px solid #e2e8f0;
        }}
        div[data-testid="stMetricValue"] {{
            color: {ACCENT};
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def account_lines(df: pd.DataFrame) -> list[str]:
    from_data = {line for line in df["line"].unique() if line}
    return sorted(set(KNOWN_LINES) | from_data)


def item_ranking(df: pd.DataFrame) -> list[str]:
    totals = (
        df.groupby("item", as_index=False)["amount"]
        .sum()
        .sort_values("amount", ascending=False)
    )
    return totals["item"].tolist()


def apply_top_items(
    grouped: pd.DataFrame, top_n: int, show_other: bool
) -> pd.DataFrame:
    totals = grouped.groupby("item")["amount"].sum().sort_values(ascending=False)
    keep = set(totals.head(top_n).index)
    out = grouped.copy()
    out["series"] = out["item"].where(out["item"].isin(keep), "Прочее")
    out = out.groupby(["period", "series"], as_index=False)["amount"].sum()
    if not show_other:
        out = out[out["series"] != "Прочее"]
    return out


def build_chart(
    data: pd.DataFrame,
    chart_label: str,
    granularity: str,
    as_share: bool = False,
) -> go.Figure:
    cfg = CHART_TYPES[chart_label]
    period_label = "Месяц" if granularity == "month" else "День"
    hover = "%{x|%d.%m.%Y}<br>%{fullData.name}: %{y:,.0f}<extra></extra>"

    if cfg["kind"] == "bar":
        fig = px.bar(
            data,
            x="period",
            y="amount",
            color="series",
            barmode=cfg["barmode"],
            labels={"period": period_label, "amount": "Доход", "series": "Статья"},
        )
    elif cfg["kind"] == "line":
        fig = px.line(
            data,
            x="period",
            y="amount",
            color="series",
            markers=True,
            labels={"period": period_label, "amount": "Доход", "series": "Статья"},
        )
    else:
        fig = px.area(
            data,
            x="period",
            y="amount",
            color="series",
            labels={"period": period_label, "amount": "Доход", "series": "Статья"},
        )

    y_title = "Доход, ₽"
    y_tick = ",.0f"
    if as_share and cfg["kind"] in ("bar", "area"):
        fig.update_layout(barnorm="percent")
        y_title = "Доля дохода"
        y_tick = ".0%"

    fig.update_layout(
        template="plotly_white",
        font_family=FONT,
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        margin=dict(l=24, r=24, t=48, b=24),
        xaxis=dict(showgrid=True, gridcolor="#f1f5f9"),
        yaxis=dict(
            title=y_title,
            tickformat=y_tick,
            showgrid=True,
            gridcolor="#f1f5f9",
        ),
        colorway=[
            ACCENT,
            "#0284C7",
            "#7C3AED",
            "#DB2777",
            "#EA580C",
            MUTED,
        ],
    )
    fig.update_traces(hovertemplate=hover)
    if granularity == "month":
        fig.update_xaxes(tickformat="%b %Y", dtick="M1")
    return fig


@st.cache_data(show_spinner="Загрузка отчёта…")
def get_data(report_path: str) -> pd.DataFrame:
    return load_turnover(report_path)


def main() -> None:
    st.set_page_config(
        page_title="Доходы — дашборд",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    inject_styles()

    st.title("Динамика поступлений")
    st.caption(
        "Доход. Цвета — доли по статьям (item). "
        "Счета и объекты — в фильтрах."
    )

    report_path = str(DEFAULT_REPORT)

    try:
        raw = get_data(report_path)
    except FileNotFoundError:
        st.error(f"Файл не найден: `{report_path}`")
        st.stop()
    except ValueError as exc:
        st.error(str(exc))
        st.stop()

    if raw.empty:
        st.warning("После фильтрации пустых amount данных нет.")
        st.stop()

    min_date = raw["date"].min().date()
    max_date = raw["date"].max().date()

    st.sidebar.header("Период")
    date_from, date_to = st.sidebar.slider(
        "Диапазон дат",
        min_value=min_date,
        max_value=max_date,
        value=(min_date, max_date),
        format="DD.MM.YYYY",
    )

    granularity = st.sidebar.radio(
        "Детализация по оси X",
        options=["month", "day"],
        format_func=lambda x: "По месяцам" if x == "month" else "По дням",
        horizontal=True,
    )

    st.sidebar.header("Фильтры")

    all_lines = account_lines(raw)
    selected_lines = st.sidebar.multiselect(
        "Счета (line)",
        options=all_lines,
        default=all_lines,
    )

    all_objs = sorted(
        {o for o in raw["obj"].unique() if o},
        key=str,
    )
    selected_objs = st.sidebar.multiselect(
        "Объекты (obj)",
        options=all_objs,
        default=all_objs,
    )

    ranked_items = item_ranking(raw)
    selected_items = st.sidebar.multiselect(
        "Статьи (item) — сверху крупнее по сумме",
        options=ranked_items,
        default=ranked_items,
    )

    st.sidebar.header("График")
    chart_label = st.sidebar.selectbox(
        "Тип диаграммы",
        options=list(CHART_TYPES.keys()),
    )
    item_count = max(1, len(ranked_items))
    top_n = st.sidebar.number_input(
        "Топ статей на графике",
        min_value=1,
        max_value=item_count,
        value=min(5, item_count),
    )
    show_other = st.sidebar.checkbox("Показать «Прочее»", value=True)
    as_share = st.sidebar.checkbox(
        "Показать доли (100% в каждом периоде)",
        value=False,
        help="Для столбчатой и областной диаграммы: высота сегмента = доля статьи в периоде.",
    )

    filtered = raw[
        raw["line"].isin(selected_lines)
        & raw["obj"].isin(selected_objs)
        & raw["item"].isin(selected_items)
        & (raw["date"].dt.date >= date_from)
        & (raw["date"].dt.date <= date_to)
    ]

    if filtered.empty:
        st.warning("Нет данных для выбранных фильтров.")
        st.stop()

    if granularity == "month":
        filtered = filtered.assign(
            period=filtered["date"].dt.to_period("M").dt.to_timestamp()
        )
    else:
        filtered = filtered.assign(period=filtered["date"].dt.normalize())

    grouped = (
        filtered.groupby(["period", "item"], as_index=False)["amount"]
        .sum()
        .sort_values("period")
    )
    chart_data = apply_top_items(grouped, int(top_n), show_other)

    total_income = filtered["amount"].sum()
    periods_count = chart_data["period"].nunique()

    m1, m2, m3 = st.columns(3)
    m1.metric("Доход за период", f"{total_income:,.0f} ₽".replace(",", " "))
    m2.metric("Строк в выборке", f"{len(filtered):,}".replace(",", " "))
    m3.metric("Периодов на графике", periods_count)

    use_share = as_share and CHART_TYPES[chart_label]["kind"] in ("bar", "area")
    fig = build_chart(chart_data, chart_label, granularity, as_share=use_share)
    st.plotly_chart(fig, use_container_width=True)

    with st.expander("Данные графика"):
        st.dataframe(
            chart_data.sort_values(["period", "amount"], ascending=[True, False]),
            use_container_width=True,
        )


if __name__ == "__main__":
    main()
