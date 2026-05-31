"""
产线 OEE 分析与瓶颈识别系统 - Streamlit 数字化看板
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from main import (
    load_data,
    generate_oee_report, identify_bottleneck,
    analyze_failure_modes, IE_SUGGESTIONS, FAILURE_MODE_MAP,
)

# ── 页面配置 ─────────────────────────────────────────────────

st.set_page_config(page_title="OEE 产线分析系统", layout="wide")

# ── 全局 CSS ─────────────────────────────────────────────────

st.markdown("""
<style>
    .stApp { font-family: "Microsoft YaHei", "PingFang SC", sans-serif; }

    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #e3f2fd 0%, #bbdefb 100%);
    }
    [data-testid="stSidebar"] .stRadio label span { color: #1a237e; font-size: 15px; }
    [data-testid="stSidebar"] .stMarkdown p { color: #37474f; font-size: 13px; }
    [data-testid="stSidebar"] .stMarkdown h2 { color: #1565c0; }

    [data-testid="stMetric"] {
        background: #ffffff; border-radius: 12px; padding: 16px 20px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06); border-left: 4px solid #1565c0;
    }
    [data-testid="stMetric"] label { font-size: 13px !important; color: #546e7a !important; }
    [data-testid="stMetric"] [data-testid="stMetricValue"] { font-size: 28px !important; font-weight: 700 !important; }

    .section-header {
        font-size: 18px; font-weight: 600; color: #1a237e;
        padding: 8px 0 4px 0; margin: 24px 0 12px 0;
        border-bottom: 2px solid #e8eaf6;
    }

    .bottleneck-card {
        background: linear-gradient(135deg, #ffebee 0%, #ffcdd2 100%);
        border-radius: 12px; padding: 20px 24px; margin: 8px 0 20px 0;
        border-left: 5px solid #c62828;
    }
    .bottleneck-card .title { font-size: 18px; font-weight: 700; color: #b71c1c; margin-bottom: 8px; }
    .bottleneck-card .detail { font-size: 14px; color: #424242; line-height: 1.8; }

    .ie-card {
        background: #f5f5f5; border-radius: 10px; padding: 14px 18px;
        margin: 8px 0; border-left: 4px solid #1565c0;
    }
    .ie-card.a-class { border-left-color: #c62828; background: #fff3e0; }
    .ie-card .code { font-weight: 700; color: #1a237e; font-size: 15px; }
    .ie-card .suggestion { color: #37474f; font-size: 14px; margin-top: 6px; }

    .risk-box { text-align: center; padding: 24px; border-radius: 16px; margin: 12px 0; }
    .risk-low  { background: linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%); border: 2px solid #43a047; }
    .risk-med  { background: linear-gradient(135deg, #fff8e1 0%, #ffecb3 100%); border: 2px solid #ffa000; }
    .risk-high { background: linear-gradient(135deg, #ffebee 0%, #ffcdd2 100%); border: 2px solid #e53935; }

    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    header { visibility: hidden; }
</style>
""", unsafe_allow_html=True)


# ── 数据加载（带缓存） ──────────────────────────────────────

@st.cache_data
def get_data():
    return load_data()


@st.cache_data
def get_report(df):
    return generate_oee_report(df)


@st.cache_data
def get_pareto(df):
    return analyze_failure_modes(df)


df = get_data()
report = get_report(df)
pareto = get_pareto(df)


# ── 侧边栏 ──────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## OEE 分析系统")
    st.markdown("**产线效率监控与瓶颈诊断**")
    st.markdown("---")
    page = st.radio(
        "功能导航",
        ["生产运营总览", "瓶颈工序诊断", "工艺参数模拟器"],
        label_visibility="collapsed",
    )
    st.markdown("---")
    st.markdown(f"**数据集**: AI4I 2020")
    st.markdown(f"**样本量**: {len(df):,} 条")
    st.markdown(f"**产线**: H ({len(df[df.product_type=='H']):,}) / M ({len(df[df.product_type=='M']):,}) / L ({len(df[df.product_type=='L']):,})")


# ════════════════════════════════════════════════════════════
#  工具函数
# ════════════════════════════════════════════════════════════

def make_gauge(value: float, title: str, color: str) -> go.Figure:
    """创建仪表盘图表。"""
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value * 100,
        number={"suffix": "%", "font": {"size": 28, "color": "#1a237e"}},
        title={"text": title, "font": {"size": 14, "color": "#546e7a"}},
        gauge={
            "axis": {"range": [0, 100], "tickwidth": 1, "tickcolor": "#e0e0e0"},
            "bar": {"color": color, "thickness": 0.3},
            "bgcolor": "#f5f5f5",
            "borderwidth": 0,
            "steps": [
                {"range": [0, 60], "color": "#ffcdd2"},
                {"range": [60, 80], "color": "#fff9c4"},
                {"range": [80, 100], "color": "#c8e6c9"},
            ],
            "threshold": {
                "line": {"color": "#c62828", "width": 2},
                "thickness": 0.8,
                "value": 85,
            },
        },
    ))
    fig.update_layout(height=180, margin=dict(l=20, r=20, t=50, b=10))
    return fig


def section(text: str):
    """渲染带图标的章节标题。"""
    st.markdown(f'<div class="section-header">{text}</div>', unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════
#  Page 1: 生产运营总览
# ════════════════════════════════════════════════════════════

def page_dashboard():
    st.markdown("## 生产运营总览")

    # ── 顶部核心指标 ──
    avg_oee = report["oee"].mean()
    avg_a = report["availability"].mean()
    avg_p = report["performance"].mean()
    avg_q = report["quality"].mean()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("全线 OEE", f"{avg_oee:.1%}", help="Availability x Performance x Quality")
    c2.metric("Availability", f"{avg_a:.1%}", help="时间利用率")
    c3.metric("Performance", f"{avg_p:.1%}", help="性能效率")
    c4.metric("Quality", f"{avg_q:.1%}", help="合格率")

    section("产线 OEE 三维指标对比")

    # ── 产线仪表盘 ──
    gauge_cols = st.columns(3)
    colors = ["#1565c0", "#2e7d32", "#e65100"]
    for i, (_, row) in enumerate(report.iterrows()):
        with gauge_cols[i]:
            fig = make_gauge(row["oee"], f"{row['product_type']} 线 OEE", colors[i])
            st.plotly_chart(fig, use_container_width=True)

    # ── 分组柱状图 ──
    chart_data = report.melt(
        id_vars="product_type",
        value_vars=["availability", "performance", "quality", "oee"],
        var_name="指标", value_name="数值",
    )
    label_map = {"availability": "Availability", "performance": "Performance",
                 "quality": "Quality", "oee": "OEE"}
    chart_data["指标"] = chart_data["指标"].map(label_map)

    fig = px.bar(
        chart_data, x="product_type", y="数值", color="指标",
        barmode="group", text_auto=".1%",
        color_discrete_sequence=["#42A5F5", "#66BB6A", "#FFA726", "#EF5350"],
        labels={"product_type": "产线", "数值": "百分比"},
    )
    fig.update_layout(
        yaxis_tickformat=".0%", yaxis_range=[0.88, 1.0],
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
        plot_bgcolor="rgba(0,0,0,0)", yaxis_gridcolor="#e0e0e0",
        height=380,
    )
    st.plotly_chart(fig, use_container_width=True)

    # ── 明细表 ──
    section("产线明细数据")
    display = report.copy()
    display.columns = ["产线", "样本量", "故障次数", "换刀次数", "缺陷数",
                       "Availability", "Performance", "Quality", "OEE"]
    for col in ["Availability", "Performance", "Quality", "OEE"]:
        display[col] = display[col].apply(lambda x: f"{x:.2%}")
    st.dataframe(display, use_container_width=True, hide_index=True, height=150)


# ════════════════════════════════════════════════════════════
#  Page 2: 瓶颈工序诊断
# ════════════════════════════════════════════════════════════

def page_diagnostic():
    st.markdown("## 瓶颈工序诊断")

    # ── 瓶颈定位卡片 ──
    bn = identify_bottleneck(report)
    st.markdown(f"""
    <div class="bottleneck-card">
        <div class="title">最低效产线: {bn['product_type']} 线  |  OEE = {bn['oee']:.1%}</div>
        <div class="detail">
            核心瓶颈指标: <b>{bn['bottleneck_metric']}</b> = {bn['bottleneck_value']:.1%}<br>
            Availability = {bn['metrics']['Availability']:.1%} &nbsp;|&nbsp;
            Performance = {bn['metrics']['Performance']:.1%} &nbsp;|&nbsp;
            Quality = {bn['metrics']['Quality']:.1%}
        </div>
    </div>
    """, unsafe_allow_html=True)

    section("失效模式 Pareto 分析")

    # ── Pareto 图（柱状 + 累计折线）──
    bar_colors = ["#c62828" if p <= 0.80 else "#90a4ae"
                  for p in pareto["cum_pct"]]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=pareto["code"], y=pareto["count"], name="频次",
        marker_color=bar_colors, text=pareto["count"],
        textposition="outside", textfont=dict(size=13, color="#37474f"),
    ))
    fig.add_trace(go.Scatter(
        x=pareto["code"], y=pareto["cum_pct"], name="累计占比",
        yaxis="y2", mode="lines+markers",
        marker=dict(size=9, color="#e53935"),
        line=dict(color="#e53935", width=2.5),
    ))
    # 80% 参考线
    fig.add_hline(y=0.80, yref="y2", line_dash="dash",
                  line_color="#ff8f00", opacity=0.6,
                  annotation_text="80% 分界线", annotation_position="top right")
    fig.update_layout(
        yaxis=dict(title="频次", side="left", gridcolor="#e0e0e0"),
        yaxis2=dict(title="累计占比", side="right", overlaying="y",
                    tickformat=".0%", range=[0, 1.08]),
        legend=dict(x=0.6, y=1.15, orientation="h"),
        plot_bgcolor="rgba(0,0,0,0)", height=420,
    )
    st.plotly_chart(fig, use_container_width=True)

    # ── Pareto 表格 ──
    p_display = pareto.copy()
    p_display.columns = ["模式", "名称", "频次", "占比", "累计占比"]
    p_display["占比"] = p_display["占比"].apply(lambda x: f"{x:.1%}")
    p_display["累计占比"] = p_display["累计占比"].apply(lambda x: f"{x:.1%}")
    st.dataframe(p_display, use_container_width=True, hide_index=True, height=210)

    # ── IE 改善建议 ──
    section("IE 智能改善建议")
    for _, row in pareto.iterrows():
        code = row["code"]
        is_a = row["cum_pct"] <= 0.80
        tag = "A类主因" if is_a else "次要因素"
        css_class = "ie-card a-class" if is_a else "ie-card"
        st.markdown(f"""
        <div class="{css_class}">
            <span class="code">{code} — {row['label']}</span>
            &nbsp;&nbsp;频次 {row['count']} 次，占比 {row['pct']:.1%}，累计 {row['cum_pct']:.1%}
            &nbsp;&nbsp;{tag}
            <div class="suggestion">{IE_SUGGESTIONS[code]}</div>
        </div>
        """, unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════
#  Page 3: 实时工艺参数模拟器
# ════════════════════════════════════════════════════════════

def page_simulator():
    st.markdown("## 实时工艺参数模拟器")
    st.caption("调节温度、转速、扭矩，实时预览质量缺陷风险等级")

    # ── 滑动条 ──
    col1, col2, col3 = st.columns(3)
    air_temp = col1.slider("环境温度 (K)", 290.0, 310.0, 300.0, 0.1)
    speed    = col2.slider("转速 (rpm)", 1000, 2800, 1500, 10)
    torque   = col3.slider("扭矩 (Nm)", 10.0, 80.0, 40.0, 0.5)

    section("参数偏离分析")

    # ── z-score 计算 ──
    stats = {
        "temp":   (df["air_temperature"].mean(), df["air_temperature"].std()),
        "speed":  (df["rotational_speed"].mean(), df["rotational_speed"].std()),
        "torque": (df["torque"].mean(), df["torque"].std()),
    }
    z_temp   = abs(air_temp - stats["temp"][0])   / stats["temp"][1]
    z_speed  = abs(speed   - stats["speed"][0])   / stats["speed"][1]
    z_torque = abs(torque  - stats["torque"][0])   / stats["torque"][1]

    # ── 偏离度指标 ──
    r1, r2, r3 = st.columns(3)
    r1.metric("环境温度偏离", f"{z_temp:.2f}σ",
              delta=f"{'↑' if air_temp > stats['temp'][0] else '↓'} 均值 {stats['temp'][0]:.1f}K",
              delta_color="off")
    r2.metric("转速偏离", f"{z_speed:.2f}σ",
              delta=f"{'↑' if speed > stats['speed'][0] else '↓'} 均值 {stats['speed'][0]:.0f}rpm",
              delta_color="off")
    r3.metric("扭矩偏离", f"{z_torque:.2f}σ",
              delta=f"{'↑' if torque > stats['torque'][0] else '↓'} 均值 {stats['torque'][0]:.1f}Nm",
              delta_color="off")

    section("质量缺陷风险评估")

    # ── 风险评估 ──
    risk_score = min((z_temp * 0.3 + z_speed * 0.3 + z_torque * 0.4) * 100, 100)

    if risk_score < 20:
        level, css_cls, advice = "低风险", "risk-low", "工艺参数在正常范围内，质量稳定。"
        gauge_color = "#2e7d32"
    elif risk_score < 50:
        level, css_cls, advice = "中风险", "risk-med", "部分参数偏离均值，建议加强巡检频率。"
        gauge_color = "#ffa000"
    else:
        level, css_cls, advice = "高风险", "risk-high", "参数严重偏离正常范围，存在质量缺陷隐患，建议立即调整！"
        gauge_color = "#c62828"

    # ── 风险仪表盘 + 雷达图 ──
    gc1, gc2 = st.columns([1, 1])

    with gc1:
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=risk_score,
            number={"suffix": " 分", "font": {"size": 36, "color": gauge_color}},
            gauge={
                "axis": {"range": [0, 100], "tickwidth": 1},
                "bar": {"color": gauge_color, "thickness": 0.35},
                "bgcolor": "#f5f5f5",
                "borderwidth": 0,
                "steps": [
                    {"range": [0, 20], "color": "#c8e6c9"},
                    {"range": [20, 50], "color": "#fff9c4"},
                    {"range": [50, 100], "color": "#ffcdd2"},
                ],
                "threshold": {
                    "line": {"color": "#37474f", "width": 2},
                    "thickness": 0.8, "value": risk_score,
                },
            },
        ))
        fig.update_layout(height=280, margin=dict(l=30, r=30, t=40, b=10))
        st.plotly_chart(fig, use_container_width=True)

    with gc2:
        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(
            r=[z_temp, z_speed, z_torque, z_temp],
            theta=["环境温度", "转速", "扭矩", "环境温度"],
            fill="toself",
            fillcolor=f"rgba({int(gauge_color[1:3],16)},{int(gauge_color[3:5],16)},{int(gauge_color[5:7],16)},0.15)",
            line_color=gauge_color, line_width=2,
            marker=dict(size=8, color=gauge_color),
        ))
        fig.update_layout(
            polar=dict(
                radialaxis=dict(visible=True, range=[0, max(4, z_temp, z_speed, z_torque) * 1.2],
                                gridcolor="#e0e0e0"),
                angularaxis=dict(gridcolor="#e0e0e0"),
            ),
            showlegend=False, height=280, margin=dict(l=60, r=60, t=30, b=30),
        )
        st.plotly_chart(fig, use_container_width=True)

    # ── 风险结论 ──
    st.markdown(f"""
    <div class="risk-box {css_cls}">
        <div style="font-size:28px; font-weight:700; color:{gauge_color};">{level}</div>
        <div style="font-size:15px; color:#424242; margin-top:8px;">{advice}</div>
    </div>
    """, unsafe_allow_html=True)


# ── 路由 ────────────────────────────────────────────────────

ROUTES = {
    "生产运营总览": page_dashboard,
    "瓶颈工序诊断": page_diagnostic,
    "工艺参数模拟器": page_simulator,
}
ROUTES[page]()
