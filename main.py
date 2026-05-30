"""
产线 OEE 分析与瓶颈识别系统 - 核心计算引擎

包含：数据接入、OEE 三维指标建模、瓶颈诊断、IE 改善建议。
"""

import os
import pandas as pd

DATA_URL = "https://archive.ics.uci.edu/ml/machine-learning-databases/00601/ai4i2020.csv"
LOCAL_CACHE = os.path.join(os.path.dirname(__file__), "ai4i2020.csv")

# 原始字段 -> 规范命名映射
COLUMN_RENAME_MAP = {
    "UDI": "uid",
    "Product ID": "product_id",
    "Type": "product_type",
    "Air temperature [K]": "air_temperature",
    "Process temperature [K]": "process_temperature",
    "Rotational speed [rpm]": "rotational_speed",
    "Torque [Nm]": "torque",
    "Tool wear [min]": "tool_wear",
    "Machine failure": "is_failure",
    "TWF": "twf_tool_wear_failure",
    "HDF": "hdf_heat_dissipation_failure",
    "PWF": "pwf_power_failure",
    "OSF": "osf_overstrain_failure",
    "RNF": "rnf_random_failure",
}


def load_data(url: str) -> pd.DataFrame:
    """从 URL 加载数据集并重命名字段，支持本地缓存。"""
    if os.path.exists(LOCAL_CACHE):
        df = pd.read_csv(LOCAL_CACHE)
    else:
        df = pd.read_csv(url)
        df.to_csv(LOCAL_CACHE, index=False)
    df.rename(columns=COLUMN_RENAME_MAP, inplace=True)
    return df


def print_data_overview(df: pd.DataFrame) -> None:
    """打印数据集的基本信息。"""
    print("=" * 60)
    print("  AI4I 2020 预测性维护数据集 - 基本信息")
    print("=" * 60)

    print(f"\n数据形状: {df.shape[0]} 行 x {df.shape[1]} 列\n")

    print("字段列表与数据类型:")
    print("-" * 40)
    for col in df.columns:
        print(f"  {col:<30s} {str(df[col].dtype):>10s}")

    print("\n前 5 条记录:")
    print("-" * 60)
    print(df.head().to_string())

    print("\n描述性统计:")
    print("-" * 60)
    print(df.describe().round(2).to_string())

    print("\n缺失值统计:")
    print("-" * 40)
    missing = df.isnull().sum()
    if missing.sum() == 0:
        print("  无缺失值")
    else:
        print(missing[missing > 0].to_string())

    print("\n故障分布 (is_failure):")
    print("-" * 40)
    print(df["is_failure"].value_counts().to_string())

    print("\n产品型号分布 (product_type):")
    print("-" * 40)
    print(df["product_type"].value_counts().to_string())

    print("\n" + "=" * 60)


# ─── 阶段二：OEE 三维指标数学建模 ───────────────────────────

PLANNED_TIME = 1440          # 单台设备单日计划生产时间（分钟）
FAILURE_DOWNTIME = 30        # 每次故障停机时长（分钟）
TOOL_WEAR_THRESHOLD = 200    # 刀具磨损触发换刀阈值（分钟）
TOOL_CHANGE_DOWNTIME = 45    # 每次换刀停机时长（分钟）
STANDARD_SPEED = 1500        # 标准理论转速（rpm）


def calc_availability(df: pd.DataFrame) -> pd.DataFrame:
    """计算 Availability（时间利用率）。

    停机损失来源：
    1. is_failure == 1 → 每次 30 分钟故障停机
    2. tool_wear 累计每达到 200 分钟 → 一次 45 分钟换刀停机
    """
    df = df.copy()
    df["_failure_downtime"] = df["is_failure"] * FAILURE_DOWNTIME
    df["_tool_changes"] = (df["tool_wear"] // TOOL_WEAR_THRESHOLD).astype(int)
    df["_tool_downtime"] = df["_tool_changes"] * TOOL_CHANGE_DOWNTIME
    return df


def calc_performance(df: pd.DataFrame) -> pd.DataFrame:
    """计算 Performance（性能效率）。

    实际转速 / 标准转速（1500 rpm），截断上限为 1.0。
    """
    df = df.copy()
    df["_performance"] = (df["rotational_speed"] / STANDARD_SPEED).clip(upper=1.0)
    return df


def calc_quality(df: pd.DataFrame) -> pd.DataFrame:
    """计算 Quality（合格率）。

    TWF/HDF/PWF/OSF 任意一项为 1 → 该产品为不合格品。
    """
    df = df.copy()
    defect_cols = ["twf_tool_wear_failure", "hdf_heat_dissipation_failure",
                   "pwf_power_failure", "osf_overstrain_failure"]
    df["_is_defect"] = df[defect_cols].any(axis=1).astype(int)
    return df


def generate_oee_report(df: pd.DataFrame) -> pd.DataFrame:
    """按产品型号分组，计算三维指标并输出结构化 OEE 报表。"""
    df = calc_availability(df)
    df = calc_performance(df)
    df = calc_quality(df)

    groups = []
    for ptype, gdf in df.groupby("product_type"):
        n = len(gdf)
        failure_downtime = gdf["_failure_downtime"].sum()
        tool_changes = gdf["_tool_changes"].sum()
        tool_downtime = gdf["_tool_downtime"].sum()
        total_downtime = failure_downtime + tool_downtime

        availability = (PLANNED_TIME - total_downtime / n) / PLANNED_TIME
        performance = gdf["_performance"].mean()
        defect_count = gdf["_is_defect"].sum()
        quality = (n - defect_count) / n
        oee = availability * performance * quality

        groups.append({
            "product_type": ptype,
            "n": n,
            "failure_count": int(gdf["is_failure"].sum()),
            "tool_changes": int(tool_changes),
            "defect_count": int(defect_count),
            "availability": round(availability, 4),
            "performance": round(performance, 4),
            "quality": round(quality, 4),
            "oee": round(oee, 4),
        })

    report = pd.DataFrame(groups).sort_values("oee", ascending=False).reset_index(drop=True)
    return report


def print_oee_report(report: pd.DataFrame) -> None:
    """格式化打印 OEE 报表。"""
    print("\n" + "=" * 80)
    print("  OEE 三维指标分析报表（按产品型号分组）")
    print("=" * 80)
    print(f"  计划时间: {PLANNED_TIME} 分钟 | 标准转速: {STANDARD_SPEED} rpm")
    print(f"  故障停机: {FAILURE_DOWNTIME} 分钟/次 | 换刀停机: {TOOL_CHANGE_DOWNTIME} 分钟/次")
    print("-" * 80)

    for _, row in report.iterrows():
        print(f"\n  【{row['product_type']} 线】  样本量: {row['n']}")
        print(f"    故障次数: {row['failure_count']}  |  换刀次数: {row['tool_changes']}  |  缺陷数: {row['defect_count']}")
        print(f"    Availability: {row['availability']:.2%}")
        print(f"    Performance:  {row['performance']:.2%}")
        print(f"    Quality:      {row['quality']:.2%}")
        print(f"    ─────────────────────────")
        print(f"    OEE:          {row['oee']:.2%}")

    # 全线平均
    avg_oee = report["oee"].mean()
    avg_a = report["availability"].mean()
    avg_p = report["performance"].mean()
    avg_q = report["quality"].mean()
    print(f"\n{'─' * 80}")
    print(f"  全线平均  Availability: {avg_a:.2%}  Performance: {avg_p:.2%}  Quality: {avg_q:.2%}  OEE: {avg_oee:.2%}")
    print("=" * 80 + "\n")


# ─── 阶段三：瓶颈诊断与 IE 智能改善建议 ────────────────────

FAILURE_MODE_MAP = {
    "twf_tool_wear_failure":       ("TWF", "刀具磨损失效"),
    "hdf_heat_dissipation_failure": ("HDF", "散热失效"),
    "pwf_power_failure":           ("PWF", "功率失效"),
    "osf_overstrain_failure":      ("OSF", "过载失效"),
    "rnf_random_failure":          ("RNF", "随机失效"),
}

IE_SUGGESTIONS = {
    "TWF": "建议实施 SMED 快速换型策略，优化换刀节拍；引入刀具寿命在线监测系统，实现预测性换刀。",
    "HDF": "建议引入智能冷却循环工装，优化温控工艺；增设散热风道或水冷模块，降低工艺温度波动。",
    "PWF": "建议排查供电回路与驱动器负载，优化功率匹配；引入功率因数校正装置。",
    "OSF": "建议优化工装夹具设计，降低过载风险；增加扭矩实时监测与过载保护联锁。",
    "RNF": "建议加强设备点检与预防性维护频率，排查间歇性故障根因（如线缆松动、传感器漂移）。",
}


def identify_bottleneck(report: pd.DataFrame) -> dict:
    """识别 OEE 最低的产线及其核心瓶颈指标。"""
    worst = report.loc[report["oee"].idxmin()]
    metrics = {
        "Availability": worst["availability"],
        "Performance": worst["performance"],
        "Quality": worst["quality"],
    }
    bottleneck_metric = min(metrics, key=metrics.get)
    return {
        "product_type": worst["product_type"],
        "oee": worst["oee"],
        "bottleneck_metric": bottleneck_metric,
        "bottleneck_value": metrics[bottleneck_metric],
        "metrics": metrics,
    }


def analyze_failure_modes(df: pd.DataFrame) -> pd.DataFrame:
    """统计五大失效模式的频次，按 Pareto 降序排列。"""
    failure_cols = list(FAILURE_MODE_MAP.keys())
    counts = df[failure_cols].sum().astype(int)
    total = counts.sum()

    rows = []
    for col, count in counts.items():
        code, label = FAILURE_MODE_MAP[col]
        rows.append({
            "code": code,
            "label": label,
            "count": count,
            "pct": round(count / total, 4) if total > 0 else 0,
        })

    pareto = pd.DataFrame(rows).sort_values("count", ascending=False).reset_index(drop=True)
    pareto["cum_pct"] = pareto["pct"].cumsum().round(4)
    return pareto


def generate_ie_suggestions(pareto: pd.DataFrame) -> list[str]:
    """根据 Pareto 分析结果，生成 IE 改善建议列表。"""
    suggestions = []
    for _, row in pareto.iterrows():
        code = row["code"]
        rank_note = ""
        if row["cum_pct"] <= 0.80:
            rank_note = " [A 类 - 主因]"
        suggestions.append(f"  {code}（{row['label']}）: 占比 {row['pct']:.1%}（累计 {row['cum_pct']:.1%}）{rank_note}")
        suggestions.append(f"    -> {IE_SUGGESTIONS[code]}")
    return suggestions


def print_diagnosis(df: pd.DataFrame, report: pd.DataFrame) -> None:
    """输出完整的瓶颈诊断报告。"""
    # 3.1 低效工序标红
    bn = identify_bottleneck(report)
    print("=" * 80)
    print("  瓶颈诊断报告")
    print("=" * 80)
    print(f"\n  [!] 最低效产线: 【{bn['product_type']} 线】  OEE = {bn['oee']:.2%}")
    print(f"      核心瓶颈指标: {bn['bottleneck_metric']} = {bn['bottleneck_value']:.2%}")
    print(f"      三维指标: A={bn['metrics']['Availability']:.2%}  P={bn['metrics']['Performance']:.2%}  Q={bn['metrics']['Quality']:.2%}")

    # 3.2 失效模式 Pareto
    pareto = analyze_failure_modes(df)
    print(f"\n{'─' * 80}")
    print("  失效模式 Pareto 分析")
    print(f"{'─' * 80}")
    total = pareto["count"].sum()
    print(f"  总缺陷事件: {total} 次\n")
    print(f"  {'模式':<6s}  {'名称':<10s}  {'频次':>6s}  {'占比':>8s}  {'累计':>8s}")
    print(f"  {'─'*6}  {'─'*10}  {'─'*6}  {'─'*8}  {'─'*8}")
    for _, row in pareto.iterrows():
        marker = " <--" if row["cum_pct"] <= 0.80 else ""
        print(f"  {row['code']:<6s}  {row['label']:<10s}  {row['count']:>6d}  {row['pct']:>7.1%}  {row['cum_pct']:>7.1%}{marker}")

    # 3.3 IE 改善建议
    print(f"\n{'─' * 80}")
    print("  IE 智能改善建议")
    print(f"{'─' * 80}")
    suggestions = generate_ie_suggestions(pareto)
    for line in suggestions:
        print(line)
    print("=" * 80 + "\n")


if __name__ == "__main__":
    print("正在从 UCI 数据库下载数据集...\n")
    df = load_data(DATA_URL)
    print_data_overview(df)

    print("\n>>> 阶段二：OEE 三维指标建模 <<<")
    report = generate_oee_report(df)
    print_oee_report(report)

    print("\n>>> 阶段三：瓶颈诊断与 IE 改善建议 <<<")
    print_diagnosis(df, report)
