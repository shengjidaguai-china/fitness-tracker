"""
体测数据模型 (v7.0 模块化拆分)
负责: 读取/解析 体脂体重.txt、增删记录、目标设定、绘图缓存、统计指标。
"""

import logging
import os
from datetime import timedelta
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd

from .constants import BODY_COLUMNS, DATA_FILE


class BodyDataModel:
    """体测数据模型 — 加载/更新 CSV 数据, 并计算关键统计指标"""

    def __init__(self):
        self.df = self._load()
        self._plot_cache: Optional[pd.DataFrame] = None  # 缓存含'日期_dt'的绘图用副本
        self.target_weight = 65.0  # 目标体重(kg) [v3.0: 12月底64.5-65.5, 取中值65.0]
        self.target_bodyfat = 12.5

    def _invalidate_cache(self):
        """数据变更后使绘图缓存失效"""
        self._plot_cache = None

    def get_plot_df(self) -> pd.DataFrame:
        """返回含'日期_dt'的绘图用 DataFrame, 复用解析结果避免每次重算

        返回浅拷贝: 调用方(如周视图需要追加'周'派生列)可直接改写,
        不会污染内部缓存对象(共享可变状态), 下次调用仍是干净副本。
        """
        if self._plot_cache is None:
            plot_df = self.df.copy()
            plot_df["日期_dt"] = pd.to_datetime(plot_df["日期"])
            self._plot_cache = plot_df.sort_values("日期_dt").reset_index(drop=True)
        return self._plot_cache.copy()

    def _load(self) -> pd.DataFrame:
        """加载体测数据,兼容旧格式(3列)和新格式(12列)"""
        if not os.path.exists(DATA_FILE):
            return pd.DataFrame(columns=BODY_COLUMNS)
        last_err: Optional[Exception] = None
        for enc in ["utf-8", "utf-8-sig", "gbk", "gb2312", "gb18030"]:
            try:
                df = pd.read_csv(DATA_FILE, encoding=enc)
                df["日期"] = pd.to_datetime(df["日期"]).dt.strftime("%Y-%m-%d")
                # 补齐缺失列
                for col in BODY_COLUMNS:
                    if col not in df.columns:
                        df[col] = np.nan
                df = df[BODY_COLUMNS].sort_values("日期").reset_index(drop=True)
                return df
            except Exception as e:  # 编码探测失败需记录, 避免静默返回空表误导为"无数据"
                last_err = e
                continue
        # 所有编码均失败: 记录真实错误(而非静默), 仍返回空表保证程序可启动
        logging.getLogger(__name__).error(f"加载数据失败, 所有编码尝试均报错: {last_err}")
        return pd.DataFrame(columns=BODY_COLUMNS)

    def save(self):
        self.df.to_csv(DATA_FILE, index=False, encoding="utf-8")

    def add_record(self, date: str, weight: float, fat: Optional[float] = None, **kwargs):
        """添加或更新记录"""
        new_row = {"日期": date, "体重(kg)": weight, "体脂率(%)": fat}
        for k, v in kwargs.items():
            if k in BODY_COLUMNS:
                new_row[k] = v
        # 合并到df
        mask = self.df["日期"] == date
        if mask.any():
            for k, v in new_row.items():
                if v is not None:
                    self.df.loc[mask, k] = v
        else:
            full_row = {col: new_row.get(col, np.nan) for col in BODY_COLUMNS}
            self.df = pd.concat([self.df, pd.DataFrame([full_row])], ignore_index=True)
        self.df = self.df.sort_values("日期").reset_index(drop=True)
        self._invalidate_cache()
        self.save()

    def delete_record(self, date: str):
        self.df = self.df[self.df["日期"] != date].reset_index(drop=True)
        self._invalidate_cache()
        self.save()

    def get_stats(self) -> Dict[str, Any]:
        """计算统计数据"""
        n = len(self.df)
        if n == 0:
            return {"count": 0}
        latest = self.df.iloc[-1]
        first = self.df.iloc[0]
        days = (pd.to_datetime(latest["日期"]) - pd.to_datetime(first["日期"])).days
        init_w = first["体重(kg)"]
        cur_w = latest["体重(kg)"]
        has_fat = self.df["体脂率(%)"].dropna()
        cur_fat = (
            latest["体脂率(%)"] if pd.notna(latest["体脂率(%)"]) else (has_fat.iloc[-1] if len(has_fat) > 0 else np.nan)
        )

        # 体脂变化：用第一个有体脂数据的记录作为起点，当前 - 初始，降低为负
        init_fat = has_fat.iloc[0] if len(has_fat) > 0 else np.nan
        fat_change = (cur_fat - init_fat) if pd.notna(init_fat) and pd.notna(cur_fat) else np.nan

        # 瘦体重
        lean = cur_w * (1 - cur_fat / 100) if pd.notna(cur_fat) else np.nan
        init_lean = (
            init_w * (1 - (first["体脂率(%)"] if pd.notna(first["体脂率(%)"]) else cur_fat) / 100)
            if pd.notna(init_w)
            else np.nan
        )

        return {
            "count": n,
            "days": days,
            "init_weight": init_w,
            "cur_weight": cur_w,
            "weight_change": cur_w - init_w,
            "cur_fat": cur_fat,
            "fat_change": fat_change,
            "cur_lean": lean,
            "lean_change": lean - init_lean if pd.notna(init_lean) else np.nan,
            "to_target_w": cur_w - self.target_weight,
            "to_target_f": cur_fat - self.target_bodyfat if pd.notna(cur_fat) else np.nan,
            "latest_date": latest["日期"],
            "first_date": first["日期"],
        }

    def predict_target_date(self, target: float, col: str = "体重(kg)") -> Optional[str]:
        """线性预测达标日"""
        valid = self.df[self.df[col].notna()].copy()
        if len(valid) < 5:
            return None
        valid["days"] = (pd.to_datetime(valid["日期"]) - pd.to_datetime(valid["日期"].iloc[0])).dt.days
        z = np.polyfit(valid["days"].values, valid[col].values, 1)
        if abs(z[0]) < 1e-6:
            return None
        pred_days = (target - z[1]) / z[0]
        if pred_days <= 0:
            return "已达"
        pred_date = pd.to_datetime(valid["日期"].iloc[0]) + timedelta(days=int(pred_days))
        return pred_date.strftime("%Y-%m-%d")
