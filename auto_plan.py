"""
输入驱动方案生成 — 命令行入口 (Issue #5)

用法:
    python auto_plan.py --weight 74 --bodyfat 23 --target-weight 68 --target-bodyfat 15 --budget 1500
    python auto_plan.py --weight 74 --bodyfat 23 --target-bodyfat 15 --budget 1500 --out 报告.md
    python auto_plan.py --help

输出: 训练计划 (含每周动作与组次) + 每日饮食计划 + 补剂方案。
方案只依赖命令行参数, 不读写任何个人数据文件, 因此可以在任何机器上直接跑。
"""

import argparse
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

from fitness_pkg.auto_plan import (
    generate_diet_markdown,
    generate_diet_plan,
    generate_training_markdown,
    generate_training_plan,
    validate_body_inputs,
    validate_budget,
)


def build_plan(args: argparse.Namespace) -> Dict[str, Any]:
    """组装完整方案 (训练 + 饮食), 输入非法时返回带 errors 的结果。"""
    check = validate_body_inputs(
        args.weight,
        args.bodyfat,
        args.target_weight,
        args.target_bodyfat,
        args.height,
        args.age,
        args.sex,
    )
    errors: List[str] = list(check["errors"])
    budget_check = validate_budget(args.budget) if args.budget is not None else {"ok": True, "errors": []}
    errors.extend(budget_check["errors"])
    if errors:
        return {"ok": False, "errors": errors}

    training = generate_training_plan(
        current_weight=check["current_weight"],
        current_bodyfat=check["current_bodyfat"],
        target_weight=check["target_weight"],
        target_bodyfat=check["target_bodyfat"],
        height_cm=check["height_cm"],
        sex=check["sex"],
        training_age_months=args.training_age_months,
        weeks=args.weeks,
        week=args.week,
    )
    diet = None
    if args.budget is not None:
        diet = generate_diet_plan(
            args.budget,
            check["current_weight"],
            check["current_bodyfat"],
            check["target_weight"],
            check["sex"],
        )
        if not diet.get("ok"):
            errors.extend(diet.get("errors", []))
            return {"ok": False, "errors": errors}

    return {
        "ok": True,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "warnings": check["warnings"],
        "training": training,
        "diet": diet,
    }


def render_markdown(plan: Dict[str, Any]) -> str:
    """渲染完整方案 Markdown。"""
    if not plan.get("ok"):
        return "\n".join(f"- ⚠ {e}" for e in plan.get("errors", ["输入无效"]))

    lines = ["# 个人训练与饮食方案", "", f"> 生成时间 {plan['generated_at']} · 由体测与预算输入自动生成", ""]
    if plan.get("warnings"):
        lines.extend(f"> ⚠ {w}" for w in plan["warnings"])
        lines.append("")
    lines.append(generate_training_markdown(plan["training"]))
    lines.append("")
    if plan.get("diet"):
        lines.append(generate_diet_markdown(plan["diet"]))
    else:
        lines.extend(["### 每日饮食计划", "", "- 未提供月度伙食费预算, 跳过饮食与补剂方案"])
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="输入当前/目标体测与月度伙食费预算, 生成训练计划 + 每日饮食计划 + 补剂方案",
    )
    parser.add_argument("--weight", required=True, help="当前体重 (kg)")
    parser.add_argument("--bodyfat", type=float, default=None, help="当前体脂率 (%%)")
    parser.add_argument("--target-weight", type=float, default=None, help="目标体重 (kg)")
    parser.add_argument("--target-bodyfat", type=float, default=None, help="目标体脂率 (%%)")
    parser.add_argument("--budget", type=float, default=None, help="每月伙食费预算 (元)")
    parser.add_argument("--height", type=float, default=None, help="身高 (cm), 用于 BMI 与等级判定")
    parser.add_argument("--age", type=int, default=None, help="年龄")
    parser.add_argument("--sex", default="male", choices=["male", "female"], help="性别 (影响体脂下限与起点负荷)")
    parser.add_argument("--training-age-months", type=int, default=0, help="训练年限 (月), 默认 0")
    parser.add_argument("--weeks", type=int, default=None, help="计划周期 (周), 默认按目标自动推算")
    parser.add_argument("--week", type=int, default=1, help="当前处于第几周 (影响减载标注)")
    parser.add_argument("--out", default=None, help="把方案写入指定 Markdown 文件")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    plan = build_plan(args)
    text = render_markdown(plan)
    print(text)
    if not plan["ok"]:
        return 2
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"\n已写入 {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
