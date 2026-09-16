"""
动作库 (v7.0 模块化拆分)
加载 exercises_matched.json + GIF 路径管理 + 首帧缩略图缓存。
"""

import json
import os
from typing import Dict, List, Optional

from PySide6.QtGui import QPixmap

from .constants import EXERCISES_JSON, GIF_DIR


class ExerciseLibrary:
    """动作库 — 加载JSON + GIF路径管理 + 预检缓存"""

    def __init__(self):
        self.exercises: List[Dict] = []
        self._gif_cache: Dict[str, Optional[str]] = {}  # media_id -> path or None
        self._gif_valid: Dict[str, bool] = {}  # media_id -> 是否有效
        self._gif_first_frame: Dict[str, bytes] = {}  # media_id -> QPixmap data
        self._load()
        self._precheck_gifs()

    def _load(self):
        if os.path.exists(EXERCISES_JSON):
            with open(EXERCISES_JSON, encoding="utf-8") as f:
                self.exercises = json.load(f)

    def _precheck_gifs(self):
        """预检所有GIF文件有效性 — 批量验证避免后续逐个检查"""
        for ex in self.exercises:
            mid = ex.get("media_id", "")
            if not mid:
                continue
            p = os.path.join(GIF_DIR, f"{mid}.gif")
            valid = False
            if os.path.exists(p) and os.path.getsize(p) > 0:
                # 仅当 QApplication 已初始化时才用 QMovie 深度校验
                from PySide6.QtWidgets import QApplication

                if QApplication.instance() is not None:
                    try:
                        from PySide6.QtGui import QMovie

                        movie = QMovie(p)
                        valid = movie.isValid() and movie.frameCount() >= 1
                        movie.setPaused(True)
                    except Exception:
                        valid = False
                else:
                    # 无 QApplication 时仅做文件存在检查
                    valid = True
            self._gif_cache[mid] = p if valid else None
            self._gif_valid[mid] = valid

    def get_by_media_id(self, media_id: str) -> Optional[Dict]:
        for ex in self.exercises:
            if ex.get("media_id") == media_id:
                return ex
        return None

    def get_by_name(self, name_cn: str) -> Optional[Dict]:
        for ex in self.exercises:
            if ex.get("name_cn") == name_cn:
                return ex
        return None

    def search(self, keyword: str) -> List[Dict]:
        kw = keyword.lower().strip()
        if not kw:
            return self.exercises
        return [
            e
            for e in self.exercises
            if kw in (e.get("name_cn") or "").lower()
            or kw in (e.get("name_en") or "").lower()
            or kw in (e.get("target") or "").lower()
            or kw in (e.get("category") or "").lower()
        ]

    def gif_path(self, media_id: str) -> Optional[str]:
        """获取GIF路径 — 使用预检缓存快速返回"""
        if not media_id:
            return None
        if media_id in self._gif_cache:
            return self._gif_cache[media_id]
        # 回退: 直接检查文件
        p = os.path.join(GIF_DIR, f"{media_id}.gif")
        valid = os.path.exists(p) and os.path.getsize(p) > 0
        self._gif_cache[media_id] = p if valid else None
        self._gif_valid[media_id] = valid
        return p if valid else None

    def has_gif(self, media_id: str) -> bool:
        """快速判断是否有可用GIF"""
        if not media_id:
            return False
        if media_id in self._gif_valid:
            return self._gif_valid[media_id]
        return self.gif_path(media_id) is not None

    def get_first_frame(self, media_id: str) -> Optional[QPixmap]:
        """获取GIF首帧QPixmap — 用于缩略图, 缓存避免重复IO (使用QImageReader)"""
        if not media_id:
            return None
        if media_id in self._gif_first_frame:
            data = self._gif_first_frame[media_id]
            pm = QPixmap()
            pm.loadFromData(data)
            if not pm.isNull():
                return pm
            # 缓存损坏, 清除并重读
            del self._gif_first_frame[media_id]
        gif_path = self.gif_path(media_id)
        if gif_path is None:
            return None
        try:
            from PySide6.QtCore import QBuffer, QByteArray, QIODevice
            from PySide6.QtGui import QImageReader

            reader = QImageReader(gif_path)
            reader.setAutoTransform(True)
            img = reader.read()  # 读取首帧
            if img.isNull():
                return None
            pm = QPixmap.fromImage(img)
            if pm and not pm.isNull():
                # 缓存为 PNG 字节串供后续复用
                qba = QByteArray()
                buf = QBuffer(qba)
                buf.open(QIODevice.WriteOnly)
                pm.save(buf, "PNG")
                buf.close()
                self._gif_first_frame[media_id] = bytes(qba)
            return pm
        except Exception:
            return None
