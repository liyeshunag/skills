#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试用例格式校验脚本

用于验证生成的 CSV 测试用例文件是否符合规范要求。
校验项包括：
- 文件编码和格式
- 字段完整性
- 用例编号规则
- 优先级合法性
- 必填字段完整性
- 重复用例检测
"""

import csv
import re
import sys
import os
from collections import Counter


class TestcaseValidator:
    """测试用例格式校验器"""

    # 必填字段（索引位置）
    REQUIRED_FIELDS = ['测试用例序号', '模块', '测试点', '测试用例标题', '优先级', '操作步骤', '预期结果']
    # 可空字段
    NULLABLE_FIELDS = ['最终结果', '备注', '测试人']
    # 合法优先级值
    VALID_PRIORITIES = {'P0', 'P1', 'P2', 'P3', 'P4'}
    # 用例序号正则
    TC_ID_PATTERN = re.compile(r'^tc_\d{3}$')

    def __init__(self, filepath):
        self.filepath = filepath
        self.errors = []
        self.warnings = []
        self.rows = []
        self.headers = []

    def validate(self) -> bool:
        """执行全部校验，返回是否通过"""
        if not self._check_file_exists():
            return False

        self._check_file_naming()

        if not self._check_encoding():
            return False

        if not self._read_csv():
            return False

        self._check_headers()
        self._check_tc_ids()
        self._check_priority()
        self._check_required_fields()
        self._check_duplicates()
        self._check_title_quality()

        return self._report()

    def _check_file_exists(self) -> bool:
        if not os.path.exists(self.filepath):
            self.errors.append(f"文件不存在: {self.filepath}")
            return False
        return True

    def _check_file_naming(self):
        """检查文件命名是否符合规范"""
        filename = os.path.basename(self.filepath)
        # 必须包含 _testcase.csv
        if not filename.endswith('_testcase.csv'):
            self.errors.append(f"文件命名不规范: {filename}。必须以 '_testcase.csv' 结尾")
        # 不能是裸的 testcase.csv
        if filename == 'testcase.csv':
            self.errors.append(f"文件名缺少项目名称: {filename}。格式应为 '项目名称_testcase.csv'")

    def _check_encoding(self) -> bool:
        """检查文件编码"""
        try:
            with open(self.filepath, 'r', encoding='utf-8-sig') as f:
                f.read(100)
            return True
        except UnicodeDecodeError:
            try:
                with open(self.filepath, 'r', encoding='utf-8') as f:
                    f.read(100)
                self.warnings.append("文件编码为 UTF-8 无 BOM，建议使用 UTF-8 BOM 以确保 Excel 兼容性")
                return True
            except UnicodeDecodeError:
                self.errors.append(f"文件编码无法识别，请使用 UTF-8 编码")
                return False

    def _read_csv(self) -> bool:
        """读取 CSV 文件内容"""
        try:
            with open(self.filepath, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                self.headers = reader.fieldnames
                if self.headers is None:
                    self.errors.append("无法读取 CSV 表头")
                    return False
                self.rows = list(reader)
            return True
        except Exception as e:
            self.errors.append(f"CSV 文件解析失败: {e}")
            return False

    def _check_headers(self):
        """检查表头字段是否完整且顺序正确"""
        expected = ['测试用例序号', '模块', '测试点', '测试用例标题', '优先级', '操作步骤', '预期结果', '最终结果', '备注', '测试人']

        if len(self.headers) != len(expected):
            self.errors.append(f"字段数量不正确：期望 {len(expected)} 个，实际 {len(self.headers)} 个")
            return

        for i, (actual, expect) in enumerate(zip(self.headers, expected)):
            if actual.strip() != expect:
                self.errors.append(f"字段名称不匹配：第{i+1}列期望「{expect}」，实际「{actual}」")

    def _check_tc_ids(self):
        """检查用例序号规则"""
        ids = []
        for row in self.rows:
            tc_id = row.get('测试用例序号', '').strip()
            ids.append(tc_id)

            if not tc_id:
                self.errors.append(f"存在空的测试用例序号")
                continue

            if not self.TC_ID_PATTERN.match(tc_id):
                self.errors.append(f"用例序号格式错误: {tc_id}，期望格式如 tc_001")
                continue

        # 检查连续性
        valid_ids = [x for x in ids if self.TC_ID_PATTERN.match(x)]
        if valid_ids:
            nums = [int(x.replace('tc_', '')) for x in valid_ids]
            expected_nums = list(range(1, len(nums) + 1))
            if nums != expected_nums:
                for i, (actual, expected) in enumerate(zip(nums, expected_nums)):
                    if actual != expected:
                        self.errors.append(f"用例序号不连续：期望 tc_{expected:03d}，实际 {valid_ids[i]}")
                        break

            # 检查重复
            duplicates = [x for x, c in Counter(ids).items() if c > 1]
            for dup in duplicates:
                self.errors.append(f"用例序号重复: {dup} 出现 {Counter(ids)[dup]} 次")

    def _check_priority(self):
        """检查优先级合法性"""
        for row in self.rows:
            tc_id = row.get('测试用例序号', '?')
            priority = row.get('优先级', '').strip()
            if priority and priority not in self.VALID_PRIORITIES:
                self.errors.append(f"[{tc_id}] 优先级非法: {priority}，只能是 P0/P1/P2/P3/P4")

    def _check_required_fields(self):
        """检查必填字段是否有空值"""
        for row in self.rows:
            tc_id = row.get('测试用例序号', '?')
            for field in self.REQUIRED_FIELDS:
                value = row.get(field, '').strip()
                if not value:
                    self.errors.append(f"[{tc_id}] 必填字段「{field}」为空")

    def _check_duplicates(self):
        """检查重复用例（标题+模块+测试点完全相同视为重复）"""
        seen = set()
        for row in self.rows:
            tc_id = row.get('测试用例序号', '?')
            title = row.get('测试用例标题', '').strip()
            module = row.get('模块', '').strip()
            test_point = row.get('测试点', '').strip()
            key = (module, test_point, title)
            if key in seen:
                self.warnings.append(f"[{tc_id}] 疑似重复用例：模块={module}, 测试点={test_point}, 标题={title}")
            seen.add(key)

    def _check_title_quality(self):
        """检查标题质量"""
        # 检查是否包含过于模糊的标题
        fuzzy_patterns = [
            r'测试一下',
            r'验证.*是否正常',
            r'测试.*功能',
            r'看看.*行不行',
            r'试一下',
        ]
        for row in self.rows:
            tc_id = row.get('测试用例序号', '?')
            title = row.get('测试用例标题', '')
            for pattern in fuzzy_patterns:
                if re.search(pattern, title):
                    self.warnings.append(f"[{tc_id}] 标题过于模糊: {title}")
                    break

    def _report(self) -> bool:
        """输出校验报告"""
        print(f"\n{'='*60}")
        print(f"  测试用例格式校验报告")
        print(f"  文件: {self.filepath}")
        print(f"{'='*60}\n")

        # 基础统计
        print(f"[统计]")
        print(f"  用例总数: {len(self.rows)}")
        if self.rows:
            priorities = Counter(row.get('优先级', '?') for row in self.rows)
            modules = Counter(row.get('模块', '?') for row in self.rows)
            print(f"  优先级分布: {dict(priorities)}")
            print(f"  覆盖模块: {list(modules.keys())}")
        print()

        # 错误
        if self.errors:
            print(f"[错误] {len(self.errors)} 项")
            for i, err in enumerate(self.errors, 1):
                print(f"  ❌ {err}")
            print()

        # 警告
        if self.warnings:
            print(f"[警告] {len(self.warnings)} 项")
            for i, warn in enumerate(self.warnings, 1):
                print(f"  ⚠️  {warn}")
            print()

        passed = len(self.errors) == 0
        if passed:
            print("✅ 校验通过！测试用例格式符合规范。")
        else:
            print("❌ 校验未通过！请根据以上错误信息修正测试用例。")

        print(f"\n{'='*60}\n")
        return passed


def main():
    if len(sys.argv) < 2:
        print("用法: python testcase-validator.py <testcase.csv>")
        print("示例: python testcase-validator.py AI医疗助手_testcase.csv")
        sys.exit(1)

    filepath = sys.argv[1]
    validator = TestcaseValidator(filepath)
    passed = validator.validate()
    sys.exit(0 if passed else 1)


if __name__ == '__main__':
    main()
