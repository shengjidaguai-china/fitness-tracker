"""pytest 共享 fixture — 健身监控项目

- 无头(Qt offscreen)环境变量, 保证 GUI 模块可导入
- 数据模型临时 CSV / 解析器临时训练计划 md
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

# 3 行旧格式体测数据(日期|体重|体脂), 覆盖 31 天窗口
SAMPLE_BODY_CSV = "日期,体重(kg),体脂率(%)\n2026-05-01,74.0,23.0\n2026-05-15,73.0,22.0\n2026-06-01,72.0,21.5\n"


@pytest.fixture
def data_csv(tmp_path):
    """写入临时体测 CSV, 返回路径字符串"""
    p = tmp_path / "体脂体重.txt"
    p.write_text(SAMPLE_BODY_CSV, encoding="utf-8")
    return str(p)


@pytest.fixture
def model(data_csv, monkeypatch):
    """指向临时 CSV 的 BodyDataModel 实例(每测试隔离)"""
    monkeypatch.setattr("fitness_pkg.data_model.DATA_FILE", data_csv)
    from fitness_pkg.data_model import BodyDataModel

    return BodyDataModel()


@pytest.fixture
def plan_md(tmp_path):
    """最小训练计划 md — 覆盖第九章(海豹)与第十章(囚徒)表格解析"""
    text = (
        "## 五、Phase 1 训练明细\n"
        "### 周一 背\n"
        "| 动作 | 组×次 | 要点 |\n"
        "| --- | --- | --- |\n"
        "\n"
        "## 九、海豹补位\n"
        "> **定位**：哑铃/杠铃缺失时的徒手补位动作库\n"
        "### 9.2 循环说明\n"
        "8 轮累计 40 次\n"
        "- 应急版训练法: 每轮间隙不超过 2 分钟\n"
        "| 动作 | 目标 | 标准要点 |\n"
        "| --- | --- | --- |\n"
        "| 折刀引体 | 背 | 膝盖微屈收紧核心 |\n"
        "| 单腿蹲 | 腿 | 重心保持在脚跟 |\n"
        "\n"
        "## 十、囚徒补位\n"
        "> **定位**：囚徒健身老派动作库\n"
        "| 艺 | 阶1 | 阶5 | 阶10 | 主计划对应日 |\n"
        "| --- | --- | --- | --- | --- |\n"
        "| 俯卧撑 | 墙撑 | 标准 | 神级 | 周一/周四 |\n"
        "\n"
        "## 十一、收尾\n"
    )
    p = tmp_path / "居家平替计划_v3.0_test.md"
    p.write_text(text, encoding="utf-8")
    return str(p)
