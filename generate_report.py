"""
生成最新体测报告和图表（仅体重和体脂率）。

目标体重/体脂可经命令行参数覆盖，默认与主程序(fitness_modules.BodyDataModel)一致。
报告文案基于真实数据动态生成，不写死周期/乐观预测。
"""

import argparse
import os
import sys
from datetime import datetime

# Windows 控制台默认 GBK, 中文 print 会抛 UnicodeEncodeError; 重绑 stdout/stderr 为 UTF-8
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei"]
plt.rcParams["axes.unicode_minus"] = False

# 路径配置
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "体重体脂监控", "体脂体重.txt")
REPORT_DIR = os.path.join(BASE_DIR, "体重体脂监控", "报告")
CHART_DIR = os.path.join(BASE_DIR, "体重体脂监控", "图表")

DEFAULT_TARGET_WEIGHT = 65.0
DEFAULT_TARGET_BODYFAT = 12.5


def load_df(data_file: str) -> pd.DataFrame:
    last_err = None
    for enc in ["utf-8", "utf-8-sig", "gbk", "gb2312", "gb18030"]:
        try:
            df = pd.read_csv(data_file, encoding=enc)
            df["日期"] = pd.to_datetime(df["日期"])
            return df.sort_values("日期").reset_index(drop=True)
        except Exception as e:
            last_err = e
            continue
    # 不静默吞错, 明确告知用户
    raise OSError(f"无法读取数据文件 {data_file} (尝试的编码均失败): {last_err}")


def build_report(df: pd.DataFrame, target_w: float, target_f: float) -> str:
    stats = {
        "记录总数": len(df),
        "开始日期": df["日期"].iloc[0].strftime("%Y-%m-%d"),
        "最新日期": df["日期"].iloc[-1].strftime("%Y-%m-%d"),
    }
    lines = []
    for col, key, unit, target in [
        ("体重(kg)", "体重", "kg", target_w),
        ("体脂率(%)", "体脂率", "%", target_f),
    ]:
        data = df[col].dropna()
        if len(data) == 0:
            continue
        init, cur = float(data.iloc[0]), float(data.iloc[-1])
        change = cur - init
        stats[f"初始{key}"] = init
        stats[f"最新{key}"] = cur
        stats[f"{key}变化"] = change
        # 进度: 仅在"朝目标方向"时有意义, 否则显示距离
        if init != target:
            progress = max(0.0, min(100.0, (init - cur) / (init - target) * 100))
            progress_str = f"{progress:.1f}%"
        else:
            progress_str = "—"
        lines.append(f"""
================================================================================
{key}统计
================================================================================
初始{key}: {init:.2f} {unit}
最新{key}: {cur:.2f} {unit}
{key}变化: {change:+.2f} {unit}
目标{key}: {target:.2f} {unit}
距离目标: {cur - target:+.2f} {unit}
{key}进度: {progress_str}""")

    summary = """
================================================================================
效果总结
================================================================================"""
    if "体重变化" in stats:
        summary += f"\n累计体重变化: {stats['体重变化']:+.2f} kg"
    if "体脂率变化" in stats:
        summary += f"\n体脂率变化: {stats['体脂率变化']:+.2f}%"

    return f"""\
================================================================================
                    体测监控报告 - 最新数据
================================================================================

生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

记录总数: {stats["记录总数"]} 条
记录时间: {stats["开始日期"]} 至 {stats["最新日期"]}
{"".join(lines)}
{summary}

================================================================================
"""


def main():
    parser = argparse.ArgumentParser(description="生成体测报告与趋势图")
    parser.add_argument(
        "--target-weight", type=float, default=DEFAULT_TARGET_WEIGHT, help=f"目标体重kg (默认 {DEFAULT_TARGET_WEIGHT})"
    )
    parser.add_argument(
        "--target-bodyfat",
        type=float,
        default=DEFAULT_TARGET_BODYFAT,
        help=f"目标体脂率%% (默认 {DEFAULT_TARGET_BODYFAT})",
    )
    args = parser.parse_args()

    os.makedirs(REPORT_DIR, exist_ok=True)
    os.makedirs(CHART_DIR, exist_ok=True)

    df = load_df(DATA_FILE)
    if len(df) == 0:
        print("数据文件为空, 无内容可报告。")
        return

    report = build_report(df, args.target_weight, args.target_bodyfat)
    print(report)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = os.path.join(REPORT_DIR, f"减脂报告_{ts}.txt")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"\n报告已保存: {report_path}")

    # 图表
    fig, axes = plt.subplots(2, 1, figsize=(12, 8))
    fig.suptitle("体测数据趋势图", fontsize=18, fontweight="bold", y=0.98)

    specs = [
        (axes[0], "体重(kg)", "体重 (kg)", args.target_weight, "目标体重"),
        (axes[1], "体脂率(%)", "体脂率 (%)", args.target_bodyfat, "目标体脂率"),
    ]
    for ax, col, ylabel, target, tlabel in specs:
        if col in df.columns and df[col].notna().any():
            ax.plot(df["日期"], df[col], "o-", linewidth=2, markersize=4, label=ylabel)
            ax.axhline(y=target, color="r", linestyle="--", alpha=0.7, label=f"{tlabel}{target}")
            ax.set_ylabel(ylabel, fontsize=12)
            ax.set_title(f"{ylabel}变化趋势", fontsize=14, fontweight="bold")
            ax.legend()
            ax.grid(True, alpha=0.3)
        else:
            ax.text(0.5, 0.5, f"无{ylabel}数据", transform=ax.transAxes, ha="center", va="center")
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d"))
        ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=2))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, fontsize=8)

    plt.tight_layout()
    chart_path = os.path.join(CHART_DIR, f"减脂趋势图_{ts}.png")
    plt.savefig(chart_path, dpi=150, bbox_inches="tight")
    print(f"图表已保存: {chart_path}")


if __name__ == "__main__":
    try:
        main()
    except (OSError, KeyError, ValueError) as e:
        print(f"[错误] {e}", file=sys.stderr)
        sys.exit(1)
