#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""用户留存数据分析：读取 CSV，输出平均留存、最差时段与决策建议。"""

from __future__ import annotations

import csv
from collections import defaultdict
from datetime import datetime
from pathlib import Path


def load_rows(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = []
        for row in reader:
            row["retention_day1"] = int(row["retention_day1"])
            row["retention_day7"] = int(row["retention_day7"])
            row["retention_day30"] = int(row["retention_day30"])
            row["_reg_dt"] = datetime.strptime(
                row["registration_date"].strip(), "%Y-%m-%d"
            )
            rows.append(row)
        return rows


def mean(values: list[int]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def cohort_key(dt: datetime) -> str:
    return f"{dt.year}-{dt.month:02d}"


def main() -> None:
    base = Path(__file__).resolve().parent
    csv_path = base / "sample_data.csv"
    if not csv_path.exists():
        print(f"未找到数据文件: {csv_path}")
        return

    rows = load_rows(csv_path)
    n = len(rows)

    d1 = [r["retention_day1"] for r in rows]
    d7 = [r["retention_day7"] for r in rows]
    d30 = [r["retention_day30"] for r in rows]

    avg1, avg7, avg30 = mean(d1), mean(d7), mean(d30)

    # 按注册月份（ cohort ）汇总
    by_month: dict[str, dict[str, list]] = defaultdict(
        lambda: {"d1": [], "d7": [], "d30": []}
    )
    for r in rows:
        key = cohort_key(r["_reg_dt"])
        by_month[key]["d1"].append(r["retention_day1"])
        by_month[key]["d7"].append(r["retention_day7"])
        by_month[key]["d30"].append(r["retention_day30"])

    cohort_stats = []
    for month in sorted(by_month.keys()):
        g = by_month[month]
        cohort_stats.append(
            {
                "period": month,
                "n": len(g["d1"]),
                "avg_d1": mean(g["d1"]),
                "avg_d7": mean(g["d7"]),
                "avg_d30": mean(g["d30"]),
            }
        )

    # 最差时段：以第30天留存为主指标（长期健康度）；并列时看第7天
    worst = min(
        cohort_stats,
        key=lambda c: (c["avg_d30"], c["avg_d7"], c["avg_d1"]),
    )

    # 漏斗流失：D1→D7、D7→D30 的相对跌幅（百分点）
    drop_d1_to_d7 = (avg1 - avg7) * 100
    drop_d7_to_d30 = (avg7 - avg30) * 100
    if drop_d1_to_d7 >= drop_d7_to_d30:
        funnel_weak = "第1天到第7天之间"
        funnel_detail = (
            f"从平均 {avg1*100:.1f}% 降至 {avg7*100:.1f}%，"
            f"约流失 {drop_d1_to_d7:.1f} 个百分点。"
        )
    else:
        funnel_weak = "第7天到第30天之间"
        funnel_detail = (
            f"从平均 {avg7*100:.1f}% 降至 {avg30*100:.1f}%，"
            f"约流失 {drop_d7_to_d30:.1f} 个百分点。"
        )

    # 输出
    print("=" * 56)
    print("用户留存分析报告")
    print("=" * 56)
    print(f"\n样本量: {n} 名用户\n")
    print("【整体平均留存率】")
    print(f"  第1天留存:  {avg1 * 100:.1f}%")
    print(f"  第7天留存:  {avg7 * 100:.1f}%")
    print(f"  第30天留存: {avg30 * 100:.1f}%")
    print("\n【按注册月份（队列）留存】")
    for c in cohort_stats:
        print(
            f"  {c['period']}  人数={c['n']:2d}  "
            f"D1={c['avg_d1']*100:5.1f}%  D7={c['avg_d7']*100:5.1f}%  D30={c['avg_d30']*100:5.1f}%"
        )
    print("\n【留存最差时段】")
    print(
        f"  注册月份 {worst['period']} 的长期留存最低："
        f"D30 平均 {worst['avg_d30']*100:.1f}% "
        f"（该月样本 {worst['n']} 人）。"
    )
    print("\n【漏斗观察】")
    print(f"  流失最集中的阶段：{funnel_weak}。")
    print(f"  {funnel_detail}")
    print("\n【决策建议】")
    print(
        "  1. 优先复盘 "
        + worst["period"]
        + " 前后上线的产品改动、运营活动与获客渠道，"
        "对照该月新用户画像是否发生变化，定位拉低了长期留存的变量。"
    )
    print(
        "  2. 针对 "
        + funnel_weak
        + " 设计干预：例如新手引导、首周任务、推送与邮件节奏，"
        "用小规模 A/B 验证后再全量。"
    )
    print(
        "  3. 将 D1/D7/D30 与业务北极星指标对齐，"
        "为「最差月份」与「最弱漏斗阶段」分别设改进目标与复盘周期。"
    )
    print("\n" + "=" * 56)


if __name__ == "__main__":
    main()
