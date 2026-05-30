"""
产线 OEE 分析与瓶颈识别系统 - Streamlit 数字化看板
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from main import (
    load_data, DATA_URL,
    generate_oee_report, identify_bottleneck,
    analyze_failure_modes, generate_ie_suggestions, IE_SUGGESTIONS,
    PLANNED_TIME, STANDARD_SPEED,
)

st.set_page_config(page_title="OEE 产线分析系统", page_icon="🏭", layout="wide")


# ── 数据加载（带缓存） ──────────────────────────────────────

@st.cache_data
def get_data():
    return load_data(DATA_URL)


@st.cache_data
def get_report(df):
    return generate_oee_report(df)


@st.cache_data
def get_pareto(df):
    return analyze_failure_modes(df)


df = get_data()
report = get_report(df)
pareto = get_pareto(df)


# ── 侧边栏导航 ─────────────────────────────────────────────

page = st.sidebar.radio(
    "导航",
    ["📊 生产运营总览", "🔍 瓶颈工序诊断", "⚙️ 工艺参数模拟器"],
)
st.sidebar.markdown("---")
st.sidebar.caption("数据源: UCI AI4I 2020 Predictive Maintenance Dataset")
st.sidebar.caption(f"样本量: {len(df):,} 条 | 产线: H / M / L")


# ════════════════════════════════════════════════════════════
#  Page 1: 生产运营总览
# ════════════════════════════════════════════════════════════

def page_dashboard():
    st.title("📊 生产运营总览")

    # ── 顶部核心指标 ──
    avg_oee = report["oee"].mean()
    avg_a = report["availability"].mean()
    avg_p = report["performance"].mean()
    avg_q = report["quality"].mean()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("全线 OEE", f"{avg_oee:.1%}")
    c2.metric("Availability", f"{avg_a:.1%}")
    c3.metric("Performance", f"{avg_p:.1%}")
    c4.metric("Quality", f"{avg_q:.1%}")

    st.markdown("---")

    # ── 产线对比柱状图 ──
    st.subheader("产线 OEE 三维指标对比")

    chart_data = report.melt(
        id_vars="product_type",
        value_vars=["availability", "performance", "quality", "oee"],
        var_name="指标",
        value_name="数值",
    )
    label_map = {
        "availability": "Availability",
        "performance": "Performance",
        "quality": "Quality",
        "oee": "OEE",
    }
    chart_data["指标"] = chart_data["指标"].map(label_map)

    fig = px.bar(
        chart_data,
        x="product_type",
        y="数值",
        color="指标",
        barmode="group",
        text_auto=".1%",
        color_discrete_sequence=["#4FC3F7", "#81C784", "#FFB74D", "#E57373"],
        labels={"product_type": "产线", "数值": "百分比"},
    )
    fig.update_layout(yaxis_tickformat=".0%", yaxis_range=[0.9, 1.0], legend_title_text="")
    st.plotly_chart(fig, use_container_width=True)

    # ── 明细表 ──
    st.subheader("产线明细数据")
    display = report.copy()
    display.columns = ["产线", "样本量", "故障次数", "换刀次数", "缺陷数",
                       "Availability", "Performance", "Quality", "OEE"]
    for col in ["Availability", "Performance", "Quality", "OEE"]:
        display[col] = display[col].apply(lambda x: f"{x:.2%}")
    st.dataframe(display, use_container_width=True, hide_index=True)


# ════════════════════════════════════════════════════════════
#  Page 2: 瓶颈工序诊断
# ════════════════════════════════════════════════════════════

def page_diagnostic():
    st.title("🔍 瓶颈工序诊断")

    # ── 瓶颈定位 ──
    bn = identify_bottleneck(report)
    st.error(
        f"**最低效产线: {bn['product_type']} 线** — OEE = {bn['oee']:.1%}  |  "
        f"核心瓶颈: **{bn['bottleneck_metric']}** = {bn['bottleneck_value']:.1%}  |  "
        f"A={bn['metrics']['Availability']:.1%}  P={bn['metrics']['Performance']:.1%}  Q={bn['metrics']['Quality']:.1%}"
    )

    st.markdown("---")

    # ── Pareto 图（柱状 + 累计折线）──
    st.subheader("失效模式 Pareto 分析")

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=pareto["code"],
        y=pareto["count"],
        name="频次",
        marker_color="#42A5F5",
        text=pareto["count"],
        textposition="outside",
    ))
    fig.add_trace(go.Scatter(
        x=pareto["code"],
        y=pareto["cum_pct"],
        name="累计占比",
        yaxis="y2",
        mode="lines+markers",
        marker=dict(size=8),
        line=dict(color="#EF5350", width=2),
    ))
    fig.update_layout(
        yaxis=dict(title="频次", side="left"),
        yaxis2=dict(title="累计占比", side="right", overlaying="y",
                    tickformat=".0%", range=[0, 1.05]),
        legend=dict(x=0.7, y=1.15, orientation="h"),
        height=420,
    )
    st.plotly_chart(fig, use_container_width=True)

    # ── Pareto 表格 ──
    p_display = pareto.copy()
    p_display.columns = ["模式", "名称", "频次", "占比", "累计占比"]
    p_display["占比"] = p_display["占比"].apply(lambda x: f"{x:.1%}")
    p_display["累计占比"] = p_display["累计占比"].apply(lambda x: f"{x:.1%}")
    st.dataframe(p_display, use_container_width=True, hide_index=True)

    # ── IE 改善建议 ──
    st.subheader("IE 智能改善建议")
    for _, row in pareto.iterrows():
        code = row["code"]
        tag = "🔴 A类主因" if row["cum_pct"] <= 0.80 else ""
        with st.expander(f"{code} — {row['label']}  ({row['pct']:.1%}) {tag}"):
            st.info(IE_SUGGESTIONS[code])


# ════════════════════════════════════════════════════════════
#  Page 3: 实时工艺参数模拟器
# ════════════════════════════════════════════════════════════

def page_simulator():
    st.title("⚙️ 实时工艺参数模拟器")
    st.caption("调节温度、转速、扭矩，实时预览质量缺陷风险等级")

    # ── 滑动条 ──
    col1, col2, col3 = st.columns(3)
    air_temp = col1.slider("环境温度 (K)", 290.0, 310.0, 300.0, 0.1)
    speed = col2.slider("转速 (rpm)", 1000, 2800, 1500, 10)
    torque = col3.slider("扭矩 (Nm)", 10.0, 80.0, 40.0, 0.5)

    st.markdown("---")

    # ── 风险评估模型 ──
    # 基于数据集统计特征的 z-score 异常度评估
    stats = {
        "air_temperature":    (df["air_temperature"].mean(), df["air_temperature"].std()),
        "rotational_speed":   (df["rotational_speed"].mean(), df["rotational_speed"].std()),
        "torque":             (df["torque"].mean(), df["torque"].std()),
    }

    z_temp = abs(air_temp - stats["air_temperature"][0]) / stats["air_temperature"][1]
    z_speed = abs(speed - stats["rotational_speed"][0]) / stats["rotational_speed"][1]
    z_torque = abs(torque - stats["torque"][0]) / stats["torque"][1]

    risk_score = (z_temp * 0.3 + z_speed * 0.3 + z_torque * 0.4) * 100
    risk_score = min(risk_score, 100)

    # ── 风险等级判定 ──
    if risk_score < 20:
        level, color, advice = "低风险 🟢", "green", "工艺参数在正常范围内，质量稳定。"
    elif risk_score < 50:
        level, color, advice = "中风险 🟡", "orange", "部分参数偏离均值，建议加强巡检频率。"
    else:
        level, color, advice = "高风险 🔴", "red", "参数严重偏离正常范围，存在质量缺陷隐患，建议立即调整！"

    # ── 风险展示 ──
    r1, r2, r3 = st.columns(3)
    r1.metric("环境温度偏离", f"{z_temp:.1f}σ")
    r2.metric("转速偏离", f"{z_speed:.1f}σ")
    r3.metric("扭矩偏离", f"{z_torque:.1f}σ")

    st.markdown("---")

    st.subheader("质量缺陷风险评估")
    st.metric("综合风险评分", f"{risk_score:.0f} / 100")
    st.markdown(f"### 风险等级: :{color}[{level}]")
    st.write(advice)

    # ── 风险分布雷达图 ──
    fig = go.Figure(go.Scatterpolar(
        r=[z_temp, z_speed, z_torque],
        theta=["环境温度", "转速", "扭矩"],
        fill="toself",
        fillcolor="rgba(66, 165, 245, 0.2)",
        line_color="#42A5F5",
    ))
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 4])),
        showlegend=False,
        height=350,
    )
    st.plotly_chart(fig, use_container_width=True)


# ── 路由 ────────────────────────────────────────────────────

if page == "📊 生产运营总览":
    page_dashboard()
elif page == "🔍 瓶颈工序诊断":
    page_diagnostic()
else:
    page_simulator()
