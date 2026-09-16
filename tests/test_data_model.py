"""BodyDataModel 单元测试 — 加载/增删/统计/目标预测/绘图缓存防污染

含回归: get_plot_df 返回浅拷贝, 杜绝调用方写操作污染内部缓存。
"""

import pytest

from fitness_pkg.constants import BODY_COLUMNS


class TestLoad:
    def test_missing_file_returns_empty_frame(self, tmp_path, monkeypatch):
        monkeypatch.setattr("fitness_pkg.data_model.DATA_FILE", str(tmp_path / "不存在.txt"))
        from fitness_pkg.data_model import BodyDataModel

        m = BodyDataModel()
        assert m.df.empty
        assert list(m.df.columns) == BODY_COLUMNS

    def test_load_old_three_col_format_fills_missing_columns(self, data_csv, monkeypatch):
        monkeypatch.setattr("fitness_pkg.data_model.DATA_FILE", data_csv)
        from fitness_pkg.data_model import BodyDataModel

        m = BodyDataModel()
        assert len(m.df) == 3
        assert list(m.df.columns) == BODY_COLUMNS
        # 日期被规范化为 YYYY-MM-DD
        assert str(m.df["日期"].iloc[0]) == "2026-05-01"

    def test_load_gbk_encoded_file(self, tmp_path, monkeypatch):
        """编码回退链应能读取 GBK 文件"""
        p = tmp_path / "gbk.txt"
        p.write_bytes("日期,体重(kg)\n2026-01-01,80.0\n".encode("gbk"))
        monkeypatch.setattr("fitness_pkg.data_model.DATA_FILE", str(p))
        from fitness_pkg.data_model import BodyDataModel

        m = BodyDataModel()
        assert len(m.df) == 1
        assert m.df["体重(kg)"].iloc[0] == pytest.approx(80.0)


class TestAddUpdateDelete:
    def test_add_new_record_appends_and_roundtrips(self, model):
        model.add_record("2026-07-01", 70.0, 20.0)
        assert len(model.df) == 4

        # 重新加载(同文件)验证已持久化
        from fitness_pkg.data_model import BodyDataModel

        reloaded = BodyDataModel()
        assert len(reloaded.df) == 4
        row = reloaded.df[reloaded.df["日期"] == "2026-07-01"].iloc[0]
        assert row["体重(kg)"] == pytest.approx(70.0)

    def test_add_same_date_updates_not_appends(self, model):
        model.add_record("2026-05-01", 70.5, 22.0)
        assert len(model.df) == 3
        row = model.df[model.df["日期"] == "2026-05-01"].iloc[0]
        assert row["体重(kg)"] == pytest.approx(70.5)

    def test_add_record_optional_column_maps_to_body_column(self, model):
        extra = next(c for c in BODY_COLUMNS if c not in ("日期", "体重(kg)", "体脂率(%)"))
        model.add_record("2026-07-02", 69.8, None, **{extra: 88.0})
        row = model.df[model.df["日期"] == "2026-07-02"].iloc[0]
        assert row[extra] == pytest.approx(88.0)

    def test_add_record_unknown_kwarg_ignored(self, model):
        model.add_record("2026-07-03", 70.0, fat=19.5, 不存在的列=999)
        assert len(model.df) == 4
        assert "不存在的列" not in model.df.columns

    def test_delete_record(self, model):
        model.delete_record("2026-05-15")
        assert len(model.df) == 2
        assert "2026-05-15" not in set(model.df["日期"])


class TestStats:
    def test_empty(self, tmp_path, monkeypatch):
        monkeypatch.setattr("fitness_pkg.data_model.DATA_FILE", str(tmp_path / "空.txt"))
        from fitness_pkg.data_model import BodyDataModel

        assert BodyDataModel().get_stats() == {"count": 0}

    def test_basic_stats(self, model):
        s = model.get_stats()
        assert s["count"] == 3
        assert s["days"] == 31  # 2026-05-01 → 2026-06-01
        assert s["init_weight"] == pytest.approx(74.0)
        assert s["cur_weight"] == pytest.approx(72.0)
        assert s["weight_change"] == pytest.approx(-2.0)
        assert s["cur_fat"] == pytest.approx(21.5)
        assert s["fat_change"] == pytest.approx(-1.5)
        assert s["to_target_w"] == pytest.approx(7.0)  # 目标体重 65kg
        assert s["first_date"] == "2026-05-01"
        assert s["latest_date"] == "2026-06-01"
        # 瘦体重 = 体重×(1-体脂%)
        assert s["cur_lean"] == pytest.approx(72.0 * (1 - 0.215))


class TestPredictTargetDate:
    """预测基于全新空数据, 保证斜率/日期窗口可精确断言"""

    def _empty_model(self, tmp_path, monkeypatch):
        monkeypatch.setattr("fitness_pkg.data_model.DATA_FILE", str(tmp_path / "空.txt"))
        from fitness_pkg.data_model import BodyDataModel

        return BodyDataModel()

    def _fill_descending(self, model, n=10):
        """连续 10 天线性递减 0.1kg/天"""
        for i in range(n):
            model.add_record(f"2026-01-{i + 1:02d}", 74.0 - i * 0.1, 22.0)
        assert len(model.df) == n

    def test_insufficient_data_returns_none(self, model):
        assert model.predict_target_date(60.0) is None  # 仅 3 条 < 5

    def test_target_already_achieved(self, tmp_path, monkeypatch):
        m = self._empty_model(tmp_path, monkeypatch)
        self._fill_descending(m)
        # 当前体重已低于目标 75kg 趋势线下方 → 已达
        assert m.predict_target_date(75.0) == "已达"

    def test_forward_projection_returns_future_date(self, tmp_path, monkeypatch):
        m = self._empty_model(tmp_path, monkeypatch)
        self._fill_descending(m)
        # 斜率约 -0.1kg/天, 74→60 需约 140 天 → 2026-05-21 前后
        d = m.predict_target_date(60.0)
        assert d is not None
        assert "2026-05-01" <= d <= "2026-06-10"

    def test_flat_slope_returns_none(self, tmp_path, monkeypatch):
        m = self._empty_model(tmp_path, monkeypatch)
        for i in range(6):
            m.add_record(f"2026-02-{i + 1:02d}", 70.0, 20.0)
        # 体重恒定 → 斜率为 0 → 无法预测
        assert m.predict_target_date(65.0) is None


class TestPlotCache:
    def test_returns_sorted_frame(self, model):
        plot = model.get_plot_df()
        assert "日期_dt" in plot.columns
        dates = plot["日期_dt"].tolist()
        assert dates == sorted(dates)

    def test_shared_cache_not_polluted_by_caller(self, model):
        """回归: get_plot_df 曾直接返回缓存本体, 周视图加'周'列会污染后续调用"""
        a = model.get_plot_df()
        a["周"] = a["日期_dt"].dt.isocalendar().week.astype(int)  # 调用方写操作
        b = model.get_plot_df()
        assert "周" not in b.columns, "内部缓存被调用方写操作污染"
        assert a is not b, "应返回拷贝而非共享同一对象"

    def test_values_survive_after_mutation(self, model):
        a = model.get_plot_df()
        a.loc[0, "体重(kg)"] = 999.0
        b = model.get_plot_df()
        assert b.loc[0, "体重(kg)"] == pytest.approx(74.0)
