#!/usr/bin/env python3
"""
duplicate_checker.py - 重复检测器

职责：
  1. 读取历史 CSV 文件
  2. 读取 testcase-history.json
  3. 对新生成的测试用例进行去重检测
  4. 检测维度：标题相似度、操作步骤相似度、模块+测试点组合
  5. 过滤已存在的重复用例
  6. 返回去重后的测试用例列表

去重策略：
  - Level 1 (完全匹配): 标题完全相同 → 直接去重
  - Level 2 (高度相似): 标题相似度 > 80% → 标记为疑似重复
  - Level 3 (功能重复): 同模块 + 同测试点 → 标记为可能重复
  - Level 4 (Diff 哈希): 同一 Diff 内容不重复处理
"""

import csv
import hashlib
import json
import os
import re
from typing import List, Dict, Set, Tuple
from difflib import SequenceMatcher


class DuplicateChecker:
    """测试用例重复检测器"""

    # 相似度阈值
    TITLE_SIMILARITY_THRESHOLD = 0.8       # 标题相似度 > 80% 视为重复
    STEPS_SIMILARITY_THRESHOLD = 0.85      # 步骤相似度 > 85% 视为重复
    COMBINED_SIMILARITY_THRESHOLD = 0.75   # 综合相似度 > 75% 视为重复

    def __init__(self, history_path: str):
        """
        初始化去重检测器

        Args:
            history_path: testcase-history.json 文件路径
        """
        self.history_path = history_path
        self.history = self._load_history()
        self.existing_testcases: List[Dict] = []

    def check_and_filter(
        self,
        new_testcases: List[Dict],
        existing_csv_dir: str
    ) -> List[Dict]:
        """
        检测并过滤重复的测试用例

        Args:
            new_testcases: 新生成的测试用例列表
            existing_csv_dir: 已有 CSV 文件目录

        Returns:
            去重后的测试用例列表
        """
        # 加载已有测试用例
        self._load_existing_testcases(existing_csv_dir)

        if not self.existing_testcases:
            print("[DUP] 没有已有测试用例，所有用例均为新增")
            return new_testcases

        print(f"[DUP] 已有 {len(self.existing_testcases)} 个测试用例")

        unique_testcases = []
        duplicate_count = 0

        for tc in new_testcases:
            is_duplicate, reason = self._is_duplicate(tc)

            if is_duplicate:
                duplicate_count += 1
                print(f"[DUP] 跳过重复用例: {tc.get('测试用例标题')} - {reason}")
            else:
                unique_testcases.append(tc)

        print(f"[DUP] 去重完成: {duplicate_count} 个重复, {len(unique_testcases)} 个新增")
        return unique_testcases

    def _is_duplicate(self, testcase: Dict) -> Tuple[bool, str]:
        """
        判断单个测试用例是否重复

        Returns:
            (是否重复, 重复原因)
        """
        new_title = testcase.get("测试用例标题", "")
        new_steps = testcase.get("操作步骤", "")
        new_module = testcase.get("模块", "")
        new_test_point = testcase.get("测试点", "")

        for existing in self.existing_testcases:
            # Level 1: 标题完全相同
            if existing.get("测试用例标题", "") == new_title:
                return True, "标题完全匹配"

            # Level 2: 标题高度相似
            existing_title = existing.get("测试用例标题", "")
            title_similarity = SequenceMatcher(None, new_title, existing_title).ratio()
            if title_similarity >= self.TITLE_SIMILARITY_THRESHOLD:
                return True, f"标题高度相似 ({title_similarity:.0%})"

            # Level 3: 同模块 + 同测试点
            if (existing.get("模块") == new_module and
                    existing.get("测试点") == new_test_point):
                # 进一步检查步骤相似度
                existing_steps = existing.get("操作步骤", "")
                if existing_steps and new_steps:
                    steps_similarity = SequenceMatcher(None, new_steps, existing_steps).ratio()
                    if steps_similarity >= self.STEPS_SIMILARITY_THRESHOLD:
                        return True, f"同模块+同测试点+步骤相似 ({steps_similarity:.0%})"

            # Level 4: 综合相似度判断
            combined_score = self._calculate_combined_similarity(testcase, existing)
            if combined_score >= self.COMBINED_SIMILARITY_THRESHOLD:
                return True, f"综合相似度过高 ({combined_score:.0%})"

        return False, ""

    def _calculate_combined_similarity(self, tc1: Dict, tc2: Dict) -> float:
        """计算两个测试用例的综合相似度"""
        score = 0.0
        weight = 0.0

        # 标题相似度 (权重 40%)
        title1 = tc1.get("测试用例标题", "")
        title2 = tc2.get("测试用例标题", "")
        if title1 and title2:
            score += SequenceMatcher(None, title1, title2).ratio() * 0.4
            weight += 0.4

        # 步骤相似度 (权重 35%)
        steps1 = tc1.get("操作步骤", "")
        steps2 = tc2.get("操作步骤", "")
        if steps1 and steps2:
            score += SequenceMatcher(None, steps1, steps2).ratio() * 0.35
            weight += 0.35

        # 测试点相同 (权重 15%)
        if tc1.get("测试点") == tc2.get("测试点"):
            score += 0.15
        weight += 0.15

        # 模块相同 (权重 10%)
        if tc1.get("模块") == tc2.get("模块"):
            score += 0.1
        weight += 0.1

        if weight == 0:
            return 0.0

        return score / weight

    def _load_existing_testcases(self, csv_dir: str):
        """加载已有 CSV 中的测试用例"""
        self.existing_testcases = []

        if not os.path.isdir(csv_dir):
            return

        for filename in os.listdir(csv_dir):
            if filename.endswith(".csv") and "_TestCases" in filename:
                filepath = os.path.join(csv_dir, filename)
                self._read_csv(filepath)

    def _read_csv(self, filepath: str):
        """读取单个 CSV 文件"""
        try:
            with open(filepath, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get("测试用例序号"):
                        self.existing_testcases.append(row)
        except Exception as e:
            print(f"[WARN] 读取 CSV 失败 {filepath}: {e}")

    def _load_history(self) -> Dict:
        """加载历史记录"""
        if os.path.exists(self.history_path):
            with open(self.history_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {
            "version": "1.0.0",
            "current_index": 0,
            "generated_modules": [],
            "scanned_commits": [],
            "scanned_prs": []
        }

    def is_commit_scanned(self, commit_sha: str) -> bool:
        """检查 Commit 是否已扫描过"""
        return commit_sha in self.history.get("scanned_commits", [])

    def is_pr_scanned(self, pr_number: int) -> bool:
        """检查 PR 是否已扫描过"""
        return pr_number in self.history.get("scanned_prs", [])

    def is_module_generated(self, module_name: str) -> bool:
        """检查模块是否已生成过测试用例"""
        for m in self.history.get("generated_modules", []):
            if m.get("module") == module_name:
                return True
        return False

    def compute_diff_hash(self, diff_content: str) -> str:
        """计算 Diff 内容的哈希值"""
        return hashlib.sha256(diff_content.encode("utf-8")).hexdigest()

    def is_diff_processed(self, diff_hash: str) -> bool:
        """检查 Diff 是否已处理过"""
        return diff_hash in self.history.get("file_hashes", {})

    def get_duplicate_report(self, new_testcases: List[Dict]) -> Dict:
        """生成去重报告"""
        duplicates = []
        for tc in new_testcases:
            is_dup, reason = self._is_duplicate(tc)
            if is_dup:
                duplicates.append({
                    "testcase_title": tc.get("测试用例标题", ""),
                    "reason": reason
                })

        return {
            "total_new": len(new_testcases),
            "duplicates_found": len(duplicates),
            "unique_count": len(new_testcases) - len(duplicates),
            "duplicates": duplicates
        }


# 命令行独立运行
if __name__ == "__main__":
    import sys

    history_file = os.path.join(
        os.path.dirname(__file__), "..", "reference", "testcase-history.json"
    )

    checker = DuplicateChecker(history_file)

    # 模拟测试数据
    existing_tc = {
        "测试用例序号": "testcase_001",
        "模块": "登录",
        "测试点": "正向功能",
        "测试用例标题": "登录成功",
        "操作步骤": "1 输入用户名\n2 输入密码\n3 点击登录"
    }
    checker.existing_testcases = [existing_tc]

    test_cases = [
        {"测试用例标题": "登录成功", "模块": "登录", "测试点": "正向功能", "操作步骤": "1 输入用户名\n2 输入密码\n3 点击登录"},
        {"测试用例标题": "登录密码错误", "模块": "登录", "测试点": "反向功能", "操作步骤": "1 输入错误密码\n2 点击登录"},
    ]

    for tc in test_cases:
        is_dup, reason = checker._is_duplicate(tc)
        print(f"{tc['测试用例标题']}: {'重复' if is_dup else '不重复'} {reason}")
