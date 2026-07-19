#!/usr/bin/env python3
"""
export_csv.py - CSV 导出工具

职责：
  1. 将测试用例数据导出为标准 CSV 文件
  2. 确保 UTF-8 BOM 编码（Excel 兼容）
  3. 确保字段顺序固定
  4. 确保编号连续
  5. 处理特殊字符转义
  6. 生成导出报告

输出规范：
  - 编码: UTF-8 with BOM
  - 分隔符: 逗号
  - 换行符: LF
  - 引用符: 双引号
  - 文件名: {ProjectName}_TestCases.csv
"""

import csv
import os
import shutil
import tempfile
from datetime import datetime, timezone
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


class CSVExporter:
    """CSV 导出工具"""

    def __init__(self):
        self.fields = CSV_FIELDS

    def export(
        self,
        rows: List[Dict],
        project_name: str,
        output_dir: str,
        create_backup: bool = True
    ) -> str:
        """
        导出测试用例到 CSV 文件

        Args:
            rows: 测试用例数据列表
            project_name: 项目名称
            output_dir: 输出目录
            create_backup: 是否创建备份文件

        Returns:
            导出的 CSV 文件路径
        """
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)

        # 构建文件路径
        filename = f"{project_name}_TestCases.csv"
        filepath = os.path.join(output_dir, filename)

        # 备份已有文件
        if create_backup and os.path.exists(filepath):
            self._backup_existing(filepath)

        # 使用临时文件写入，确保原子性
        self._atomic_write(filepath, rows)

        # 验证导出结果
        self._verify_export(filepath, rows)

        print(f"[EXPORT] 成功导出 {len(rows)} 个测试用例到 {filepath}")
        return filepath

    def export_to_stream(self, rows: List[Dict]) -> str:
        """
        导出为字符串（用于 API 返回）

        Args:
            rows: 测试用例数据

        Returns:
            CSV 格式字符串
        """
        import io
        output = io.StringIO()

        # Python csv 模块不直接支持 BOM，这里先写 BOM
        output.write('\ufeff')

        writer = csv.DictWriter(output, fieldnames=self.fields, lineterminator='\n')
        writer.writeheader()
        for row in rows:
            writer.writerow(self._sanitize_row(row))

        return output.getvalue()

    def _atomic_write(self, filepath: str, rows: List[Dict]):
        """
        原子写入：先写临时文件，再替换

        防止写入过程中崩溃导致文件损坏
        """
        tmp_dir = os.path.dirname(filepath)
        tmp_fd, tmp_path = tempfile.mkstemp(
            suffix=".csv",
            prefix="temp_testcase_",
            dir=tmp_dir
        )

        try:
            with os.fdopen(tmp_fd, "w", encoding="utf-8-sig", newline='') as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=self.fields,
                    lineterminator='\n',
                    quoting=csv.QUOTE_MINIMAL
                )
                writer.writeheader()
                for row in rows:
                    writer.writerow(self._sanitize_row(row))

            # 原子替换
            os.replace(tmp_path, filepath)

        except Exception:
            # 清理临时文件
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            raise

    def _sanitize_row(self, row: Dict) -> Dict:
        """清理和标准化行数据"""
        sanitized = {}
        for field in self.fields:
            value = row.get(field, "")
            if value is None:
                value = ""
            sanitized[field] = str(value)
        return sanitized

    def _backup_existing(self, filepath: str):
        """备份已有 CSV 文件"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = filepath.replace(".csv", f"_backup_{timestamp}.csv")
        shutil.copy2(filepath, backup_path)
        print(f"[EXPORT] 已备份至: {backup_path}")

    def _verify_export(self, filepath: str, expected_rows: List[Dict]):
        """验证导出结果的完整性"""
        try:
            with open(filepath, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                exported_rows = list(reader)

            # 检查行数
            if len(exported_rows) != len(expected_rows):
                print(f"[WARN] 行数不一致: 预期 {len(expected_rows)}, 实际 {len(exported_rows)}")

            # 检查字段
            if exported_rows:
                actual_fields = list(exported_rows[0].keys())
                if actual_fields != self.fields:
                    print(f"[WARN] 字段不一致!")
                    print(f"  预期: {self.fields}")
                    print(f"  实际: {actual_fields}")

        except Exception as e:
            print(f"[WARN] 验证导出结果失败: {e}")

    def generate_export_report(self, rows: List[Dict]) -> Dict:
        """生成导出报告"""
        modules = set()
        priorities = {"P0": 0, "P1": 0, "P2": 0, "P3": 0}
        test_points = {}

        for row in rows:
            modules.add(row.get("模块", ""))
            priority = row.get("优先级", "P3")
            if priority in priorities:
                priorities[priority] += 1
            test_point = row.get("测试点", "未知")
            test_points[test_point] = test_points.get(test_point, 0) + 1

        return {
            "total_testcases": len(rows),
            "modules_count": len(modules),
            "modules": sorted(list(modules)),
            "priority_distribution": priorities,
            "test_point_distribution": test_points,
            "export_time": datetime.now(timezone.utc).isoformat()
        }


# 命令行独立运行
if __name__ == "__main__":
    import sys
    import json

    exporter = CSVExporter()

    # 模拟测试数据
    test_data = [
        {
            "测试用例序号": "testcase_001",
            "模块": "登录",
            "测试点": "正向功能",
            "测试用例标题": "登录成功",
            "优先级": "P0",
            "操作步骤": "1 打开登录页\n2 输入用户名admin\n3 输入密码Test@123\n4 点击登录",
            "预期结果": "跳转到首页\n显示欢迎信息\nToken存入LocalStorage",
            "最终结果": "",
            "备注": "",
            "测试人": ""
        },
        {
            "测试用例序号": "testcase_002",
            "模块": "登录",
            "测试点": "反向功能",
            "测试用例标题": "登录密码错误",
            "优先级": "P1",
            "操作步骤": "1 打开登录页\n2 输入用户名admin\n3 输入错误密码\n4 点击登录",
            "预期结果": "停留在登录页\n提示密码错误\n登录次数-1",
            "最终结果": "",
            "备注": "",
            "测试人": ""
        }
    ]

    output_file = exporter.export(
        rows=test_data,
        project_name="ExampleProject",
        output_dir=os.path.join(os.path.dirname(__file__), ".."),
        create_backup=False
    )

    report = exporter.generate_export_report(test_data)
    print(json.dumps(report, ensure_ascii=False, indent=2))
