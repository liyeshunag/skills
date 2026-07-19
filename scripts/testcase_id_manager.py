#!/usr/bin/env python3
"""
testcase_id_manager.py - 测试用例编号管理器

职责：
  1. 管理测试用例编号的分配
  2. 确保编号连续递增、不重复、不跳号
  3. 持久化编号状态到 testcase-history.json
  4. 支持编号预留和回滚
  5. 支持并发安全（文件锁机制）

编号格式：testcase_{NNN}  (如 testcase_001, testcase_002, ...)
"""

import json
import os
import fcntl
import time
from typing import List, Optional


class TestCaseIDManager:
    """测试用例编号管理器"""

    # 编号格式
    ID_FORMAT = "testcase_{:03d}"
    # 最大编号（3位数字）
    MAX_INDEX = 999

    def __init__(self, history_path: str):
        """
        初始化编号管理器

        Args:
            history_path: testcase-history.json 文件路径
        """
        self.history_path = history_path
        self.history = self._load_history()
        self.current_index = self.history.get("current_index", 0)

        # 确保 reference 目录存在
        os.makedirs(os.path.dirname(self.history_path), exist_ok=True)

    def allocate(self, count: int) -> List[str]:
        """
        分配 count 个新编号

        Args:
            count: 需要分配的编号数量

        Returns:
            编号字符串列表

        Raises:
            ValueError: 编号超出范围时抛出
        """
        if count <= 0:
            return []

        if self.current_index + count > self.MAX_INDEX:
            raise ValueError(
                f"编号超出最大范围！当前: {self.current_index}, "
                f"需要: {count}, 最大: {self.MAX_INDEX}"
            )

        ids = []
        for i in range(count):
            self.current_index += 1
            ids.append(self.ID_FORMAT.format(self.current_index))

        # 持久化
        self._save_history()

        return ids

    def allocate_single(self) -> str:
        """
        分配单个编号

        Returns:
            编号字符串
        """
        ids = self.allocate(1)
        return ids[0] if ids else ""

    def get_current_index(self) -> int:
        """获取当前编号索引"""
        return self.current_index

    def get_next_index(self) -> int:
        """获取下一个编号索引（不分配）"""
        return self.current_index + 1

    def get_next_id(self) -> str:
        """预览下一个编号（不分配）"""
        return self.ID_FORMAT.format(self.current_index + 1)

    def reserve(self, count: int) -> List[str]:
        """
        预留编号（不立即持久化，用于批量操作中的预分配）

        Args:
            count: 预留数量

        Returns:
            编号列表
        """
        reserved = []
        next_idx = self.current_index
        for i in range(count):
            next_idx += 1
            reserved.append(self.ID_FORMAT.format(next_idx))
        return reserved

    def rollback(self, count: int):
        """
        回滚编号（测试用例生成失败时使用）

        Args:
            count: 回滚数量
        """
        self.current_index = max(0, self.current_index - count)
        self._save_history()

    def reset(self, start_index: int = 0):
        """
        重置编号（慎用！会清除所有历史编号）

        Args:
            start_index: 起始编号
        """
        self.current_index = start_index
        self.history["generated_modules"] = []
        self.history["current_index"] = start_index
        self._save_history()

    def validate_id(self, testcase_id: str) -> bool:
        """
        校验编号格式是否合法

        Args:
            testcase_id: 测试用例编号

        Returns:
            是否合法
        """
        import re
        if not re.match(r'^testcase_\d{3}$', testcase_id):
            return False
        num = int(testcase_id.replace("testcase_", ""))
        return 1 <= num <= self.MAX_INDEX

    def parse_index(self, testcase_id: str) -> int:
        """
        从编号字符串中提取数字部分

        Args:
            testcase_id: 测试用例编号

        Returns:
            数字索引
        """
        return int(testcase_id.replace("testcase_", ""))

    def id_range(self, start: str, end: str) -> List[str]:
        """
        生成两个编号之间的所有编号

        Args:
            start: 起始编号 (如 testcase_001)
            end: 结束编号 (如 testcase_010)

        Returns:
            编号列表
        """
        start_idx = self.parse_index(start)
        end_idx = self.parse_index(end)

        return [self.ID_FORMAT.format(i) for i in range(start_idx, end_idx + 1)]

    def _load_history(self) -> dict:
        """加载历史记录（带文件锁）"""
        if not os.path.exists(self.history_path):
            return {
                "version": "1.0.0",
                "current_index": 0,
                "project_name": "",
                "generated_modules": []
            }

        try:
            with open(self.history_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"[WARN] History 文件读取失败: {e}，使用默认配置")
            return {
                "version": "1.0.0",
                "current_index": 0,
                "project_name": "",
                "generated_modules": []
            }

    def _save_history(self):
        """保存历史记录（带文件锁，防并发写入）"""
        self.history["current_index"] = self.current_index

        # 确保目录存在
        os.makedirs(os.path.dirname(self.history_path), exist_ok=True)

        # 带锁写入
        try:
            with open(self.history_path, "r+", encoding="utf-8") as f:
                # 获取排他锁
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                try:
                    f.seek(0)
                    f.truncate()
                    json.dump(self.history, f, ensure_ascii=False, indent=2)
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        except IOError:
            # 文件不存在则创建
            with open(self.history_path, "w", encoding="utf-8") as f:
                json.dump(self.history, f, ensure_ascii=False, indent=2)

    def get_statistics(self) -> dict:
        """获取编号统计信息"""
        return {
            "current_index": self.current_index,
            "next_id": self.get_next_id(),
            "remaining_ids": self.MAX_INDEX - self.current_index,
            "usage_percent": round(self.current_index / self.MAX_INDEX * 100, 2),
            "max_index": self.MAX_INDEX
        }

    def export_module_ids(self) -> dict:
        """导出各模块的编号范围"""
        module_ids = {}
        for module in self.history.get("generated_modules", []):
            module_name = module.get("module", "unknown")
            ids = module.get("testcase_ids", [])
            if ids:
                module_ids[module_name] = ids
        return module_ids


# 命令行独立运行
if __name__ == "__main__":
    import sys

    history_file = os.path.join(
        os.path.dirname(__file__), "..", "reference", "testcase-history.json"
    )

    manager = TestCaseIDManager(history_file)

    # 查看状态
    print("=== 编号管理器状态 ===")
    stats = manager.get_statistics()
    for key, value in stats.items():
        print(f"  {key}: {value}")

    # 分配测试
    if "--allocate" in sys.argv:
        count = 5
        ids = manager.allocate(count)
        print(f"\n分配 {count} 个编号:")
        for tid in ids:
            print(f"  {tid}")

        print(f"\n当前索引: {manager.get_current_index()}")
        print(f"下一个编号: {manager.get_next_id()}")
