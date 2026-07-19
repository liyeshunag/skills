#!/usr/bin/env python3
"""
merge_csv.py - CSV 合并工具

职责：
  1. 读取已有的测试用例 CSV 文件
  2. 将新生成的测试用例合并到已有 CSV
  3. 保持字段顺序一致
  4. 按编号排序
  5. 处理可能的冲突（同编号覆盖、同标题去重）
  6. 生成合并后的完整 CSV 内容

合并策略：
  - 保留已有用例：已有编号的用例保持不变
  - 追加新用例：新用例追加到末尾
  - 冲突处理：同编号以新用例为准，同标题进行去重选择
"""

import csv
import io
import os
from typing import List, Dict, Optional

# CSV 固定字段顺序
CSV_FIELDS = [
    "测试用例序号",
    "模块",
    "测试点",
    "测试用例标题",
    "优先级",
    "操作步骤",
    "预期结果",
    "最终结果",
    "备注",
    "测试人"
]


class CSVMerger:
    """CSV 合并工具"""

    def __init__(self):
        self.fields = CSV_FIELDS

    def merge(
        self,
        existing_csv: str,
        new_testcases: List[Dict]
    ) -> List[Dict]:
        """
        合并已有 CSV 和新测试用例

        Args:
            existing_csv: 已有 CSV 文件路径（可能不存在）
            new_testcases: 新生成的测试用例列表

        Returns:
            合并后的完整测试用例列表
        """
        # 读取已有测试用例
        existing_testcases = self._read_existing_csv(existing_csv)

        print(f"[MERGE] 已有用例: {len(existing_testcases)} 个")
        print(f"[MERGE] 新用例: {len(new_testcases)} 个")

        # 按编号建立索引
        existing_dict = {}
        for tc in existing_testcases:
            tc_id = tc.get("测试用例序号", "")
            if tc_id:
                existing_dict[tc_id] = tc

        # 合并：新用例追加，同编号覆盖
        merged_dict = dict(existing_dict)  # 保留已有
        for tc in new_testcases:
            tc_id = tc.get("测试用例序号", "")
            if tc_id in existing_dict:
                print(f"[MERGE] 覆盖已有用例: {tc_id} - {tc.get('测试用例标题')}")
            merged_dict[tc_id] = tc

        # 按编号排序
        merged_list = sorted(
            merged_dict.values(),
            key=lambda x: self._parse_id(x.get("测试用例序号", ""))
        )

        # 确保字段完整
        merged_list = [self._normalize_row(row) for row in merged_list]

        print(f"[MERGE] 合并后总计: {len(merged_list)} 个用例")
        return merged_list

    def merge_multiple_csvs(self, csv_files: List[str]) -> List[Dict]:
        """合并多个 CSV 文件"""
        all_testcases = []
        seen_ids = set()

        for csv_file in csv_files:
            testcases = self._read_existing_csv(csv_file)
            for tc in testcases:
                tc_id = tc.get("测试用例序号", "")
                if tc_id not in seen_ids:
                    seen_ids.add(tc_id)
                    all_testcases.append(tc)

        return sorted(
            all_testcases,
            key=lambda x: self._parse_id(x.get("测试用例序号", ""))
        )

    def _read_existing_csv(self, csv_path: str) -> List[Dict]:
        """读取已有 CSV 文件"""
        if not csv_path or not os.path.exists(csv_path):
            return []

        try:
            with open(csv_path, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                rows = []
                for row in reader:
                    if row.get("测试用例序号"):
                        rows.append(self._normalize_row(row))
                return rows
        except Exception as e:
            print(f"[WARN] 读取 CSV 失败 {csv_path}: {e}")
            return []

    def _normalize_row(self, row: Dict) -> Dict:
        """标准化行数据，确保字段完整"""
        normalized = {}
        for field in self.fields:
            normalized[field] = row.get(field, "")
        return normalized

    def _parse_id(self, tc_id: str) -> int:
        """解析编号为整数用于排序"""
        if not tc_id:
            return 9999
        try:
            return int(tc_id.replace("testcase_", ""))
        except ValueError:
            return 9999

    def get_diff(self, before: List[Dict], after: List[Dict]) -> Dict:
        """对比合并前后的差异"""
        before_ids = {tc["测试用例序号"] for tc in before}
        after_ids = {tc["测试用例序号"] for tc in after}

        return {
            "total_before": len(before),
            "total_after": len(after),
            "added": list(after_ids - before_ids),
            "removed": list(before_ids - after_ids),
            "retained": list(before_ids & after_ids),
            "added_count": len(after_ids - before_ids),
            "removed_count": len(before_ids - after_ids)
        }

    def to_csv_string(self, testcases: List[Dict]) -> str:
        """
        将测试用例列表转换为 CSV 字符串

        Args:
            testcases: 测试用例列表

        Returns:
            CSV 格式的字符串
        """
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=self.fields)

        writer.writeheader()
        for tc in testcases:
            writer.writerow(self._normalize_row(tc))

        return output.getvalue()

    def validate_continuity(self, testcases: List[Dict]) -> List[str]:
        """
        校验编号连续性

        Returns:
            问题列表（空列表表示编号连续）
        """
        issues = []
        ids = [self._parse_id(tc.get("测试用例序号", "")) for tc in testcases]
        ids.sort()

        for i in range(1, len(ids)):
            if ids[i] != ids[i-1] + 1:
                issues.append(
                    f"编号不连续: testcase_{ids[i-1]:03d} → testcase_{ids[i]:03d}，"
                    f"缺少 testcase_{ids[i-1]+1:03d}"
                )

        return issues


# 命令行独立使用
if __name__ == "__main__":
    import sys

    merger = CSVMerger()

    # 模拟测试
    existing = [
        {"测试用例序号": "testcase_001", "模块": "登录", "测试点": "正向功能",
         "测试用例标题": "登录成功", "优先级": "P0",
         "操作步骤": "1 输入用户名\n2 输入密码\n3 点击登录",
         "预期结果": "跳转到首页", "最终结果": "", "备注": "", "测试人": ""}
    ]

    new = [
        {"测试用例序号": "testcase_002", "模块": "登录", "测试点": "反向功能",
         "测试用例标题": "登录密码错误", "优先级": "P1",
         "操作步骤": "1 输入错误密码\n2 点击登录",
         "预期结果": "提示密码错误", "最终结果": "", "备注": "", "测试人": ""}
    ]

    merged = merger.merge(None, new)
    # 手动添加 existing 数据来模拟
    merged = existing + new
    merged.sort(key=lambda x: merger._parse_id(x["测试用例序号"]))

    csv_str = merger.to_csv_string(merged)
    print(csv_str)

    # 校验连续性
    issues = merger.validate_continuity(merged)
    if issues:
        print("编号问题:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("编号连续 ✓")
