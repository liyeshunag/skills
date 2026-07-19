#!/usr/bin/env python3
"""
scan_repository.py - 仓库扫描主入口

职责：
  1. 克隆/拉取 GitHub 仓库
  2. 解析命令行参数（repo/branch/commit/pr/diff）
  3. 协调各子模块完成扫描→分析→生成流程
  4. 输出最终 CSV 文件

使用方式：
  # 扫描整个仓库
  python scan_repository.py --repo https://github.com/example/helix.git --project-name Helix

  # 扫描指定 PR
  python scan_repository.py --repo https://github.com/example/helix.git --pr 42 --incremental

  # 扫描指定 Commit
  python scan_repository.py --repo https://github.com/example/helix.git --commit abc123def

  # 扫描自定义 Diff
  python scan_repository.py --diff ./changes.diff --project-name Helix
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
import hashlib
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict, Any

# 子模块导入
from parse_diff import DiffParser
from generate_testcase import TestCaseGenerator
from duplicate_checker import DuplicateChecker
from merge_csv import CSVMerger
from testcase_id_manager import TestCaseIDManager
from export_csv import CSVExporter


class RepositoryScanner:
    """GitHub 仓库扫描器 - 主入口类"""

    def __init__(self, args: argparse.Namespace):
        self.repo_url = args.repo
        self.branch = args.branch or "main"
        self.commit_sha = args.commit
        self.pr_number = args.pr
        self.diff_file = args.diff
        self.project_name = args.project_name
        self.output_dir = args.output_dir or os.getcwd()
        self.incremental = args.incremental
        self.coverage_level = args.coverage_level or "standard"

        # 工作目录
        self.work_dir = None
        self.reference_dir = os.path.join(os.path.dirname(__file__), "..", "reference")
        self.history_path = os.path.join(self.reference_dir, "testcase-history.json")

        # 子模块实例
        self.diff_parser = None
        self.testcase_generator = None
        self.duplicate_checker = None
        self.csv_merger = None
        self.id_manager = None
        self.csv_exporter = None

        # GitHub Token
        self.github_token = os.environ.get("GITHUB_TOKEN")

    def run(self) -> str:
        """
        主执行流程

        Returns:
            str: 生成的 CSV 文件路径
        """
        print(f"[INFO] 开始扫描仓库: {self.repo_url or self.diff_file}")
        print(f"[INFO] 项目名称: {self.project_name}")
        print(f"[INFO] 增量模式: {self.incremental}")

        # Step 1: 准备代码
        diff_content = self._prepare_diff()

        # Step 2: 初始化子模块
        self._init_modules()

        # Step 3: 解析 Diff
        parsed_changes = self.diff_parser.parse(diff_content)
        print(f"[INFO] 解析到 {len(parsed_changes)} 个代码变更")

        # Step 4: 识别新增功能
        new_features = self._identify_new_features(parsed_changes)
        print(f"[INFO] 识别到 {len(new_features)} 个新增功能点")

        if not new_features:
            print("[INFO] 没有新增功能，跳过测试用例生成")
            return ""

        # Step 5: 增量模式 - 过滤已生成的功能
        if self.incremental:
            new_features = self._filter_existing_features(new_features)
            print(f"[INFO] 增量过滤后剩余 {len(new_features)} 个功能点")

        if not new_features:
            print("[INFO] 所有功能已有测试用例，无需生成新的")
            return ""

        # Step 6: 分配编号
        count = sum(f["estimated_testcase_count"] for f in new_features)
        allocated_ids = self.id_manager.allocate(count)
        print(f"[INFO] 分配了 {len(allocated_ids)} 个新编号")

        # Step 7: 生成测试用例
        all_testcases = []
        id_index = 0
        for feature in new_features:
            feature_count = feature["estimated_testcase_count"]
            feature_ids = allocated_ids[id_index:id_index + feature_count]
            id_index += feature_count

            testcases = self.testcase_generator.generate(
                feature=feature,
                allocated_ids=feature_ids,
                coverage_level=self.coverage_level
            )
            all_testcases.extend(testcases)

        print(f"[INFO] 生成了 {len(all_testcases)} 个测试用例")

        # Step 8: 去重检查
        unique_testcases = self.duplicate_checker.check_and_filter(
            new_testcases=all_testcases,
            existing_csv_dir=self.output_dir
        )
        print(f"[INFO] 去重后剩余 {len(unique_testcases)} 个测试用例")

        # Step 9: 合并 CSV
        merged_rows = self.csv_merger.merge(
            existing_csv=os.path.join(self.output_dir, f"{self.project_name}_TestCases.csv"),
            new_testcases=unique_testcases
        )

        # Step 10: 导出 CSV
        output_path = self.csv_exporter.export(
            rows=merged_rows,
            project_name=self.project_name,
            output_dir=self.output_dir
        )
        print(f"[INFO] CSV 已导出至: {output_path}")

        # Step 11: 更新 History
        self._update_history(new_features, unique_testcases)

        print(f"[INFO] 扫描完成，共生成 {len(unique_testcases)} 个有效测试用例")
        return output_path

    def _prepare_diff(self) -> str:
        """准备 Diff 内容"""
        # 优先使用自定义 Diff 文件
        if self.diff_file:
            with open(self.diff_file, "r", encoding="utf-8") as f:
                return f.read()

        # 使用临时目录克隆仓库
        self.work_dir = tempfile.mkdtemp(prefix="github_scanner_")
        print(f"[INFO] 工作目录: {self.work_dir}")

        # 克隆仓库
        self._clone_repository()

        # 获取 Diff
        diff_content = self._get_git_diff()

        return diff_content

    def _clone_repository(self):
        """克隆 GitHub 仓库"""
        if not self.repo_url:
            raise ValueError("未提供仓库 URL")

        # 构造带 Token 的 URL
        clone_url = self.repo_url
        if self.github_token and "github.com" in clone_url:
            clone_url = clone_url.replace(
                "https://github.com",
                f"https://{self.github_token}@github.com"
            )

        cmd = ["git", "clone", "--depth", "50", "--branch", self.branch, clone_url, self.work_dir]
        print(f"[INFO] 克隆仓库: {' '.join(cmd[:4])} ...")
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            # 尝试不带 depth 限制
            cmd = ["git", "clone", "--branch", self.branch, clone_url, self.work_dir]
            result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            raise RuntimeError(f"仓库克隆失败: {result.stderr}")

        print("[INFO] 仓库克隆成功")

    def _get_git_diff(self) -> str:
        """获取 Git Diff 内容"""
        os.chdir(self.work_dir)

        if self.pr_number:
            # PR Diff: 获取 PR 的 base 和 head 之间的差异
            return self._get_pr_diff()
        elif self.commit_sha:
            # Commit Diff: 获取指定 commit 的变更
            cmd = ["git", "diff", f"{self.commit_sha}^", self.commit_sha]
        else:
            # 全量 Diff: 获取最近 N 个 commit 的差异
            # 首次扫描时获取所有历史
            cmd = ["git", "diff", "HEAD~50", "HEAD"]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            # 尝试获取当前分支与 main 的差异
            cmd = ["git", "diff", f"origin/{self.branch}"]
            result = subprocess.run(cmd, capture_output=True, text=True)

        return result.stdout

    def _get_pr_diff(self) -> str:
        """获取 PR 的 Diff"""
        # 使用 GitHub CLI 或 API 获取 PR Diff
        if self.github_token:
            # 使用 GitHub API
            import urllib.request
            repo_path = self.repo_url.replace("https://github.com/", "").replace(".git", "")
            api_url = f"https://api.github.com/repos/{repo_path}/pulls/{self.pr_number}"
            headers = {
                "Authorization": f"Bearer {self.github_token}",
                "Accept": "application/vnd.github.v3.diff"
            }
            req = urllib.request.Request(api_url, headers=headers)
            with urllib.request.urlopen(req) as response:
                return response.read().decode("utf-8")

        # Fallback: 尝试 gh CLI
        result = subprocess.run(
            ["gh", "pr", "diff", str(self.pr_number)],
            capture_output=True, text=True, cwd=self.work_dir
        )
        if result.returncode == 0:
            return result.stdout

        raise RuntimeError("无法获取 PR Diff，请设置 GITHUB_TOKEN 环境变量或安装 gh CLI")

    def _init_modules(self):
        """初始化所有子模块"""
        self.diff_parser = DiffParser()
        self.testcase_generator = TestCaseGenerator(
            prompt_template_dir=self.reference_dir
        )
        self.duplicate_checker = DuplicateChecker(
            history_path=self.history_path
        )
        self.csv_merger = CSVMerger()
        self.id_manager = TestCaseIDManager(
            history_path=self.history_path
        )
        self.csv_exporter = CSVExporter()

    def _identify_new_features(self, parsed_changes: List[Dict]) -> List[Dict]:
        """从解析的变更中识别新增功能"""
        features = []

        for change in parsed_changes:
            if change.get("type") == "new":
                # 估算测试用例数量（基于功能复杂度）
                estimated_count = self._estimate_testcase_count(change)
                features.append({
                    "feature_name": change.get("feature_name", "未命名功能"),
                    "module_name": change.get("module_name", "通用"),
                    "feature_description": change.get("description", ""),
                    "change_type": "new",
                    "file_path": change.get("file_path", ""),
                    "code_context": change.get("code_snippet", ""),
                    "estimated_testcase_count": estimated_count
                })

        return features

    def _estimate_testcase_count(self, change: Dict) -> int:
        """根据功能复杂度估算需要的测试用例数量"""
        complexity = change.get("complexity", "medium")

        complexity_map = {
            "low": 10,       # 简单功能，覆盖核心 10 类场景
            "medium": 18,    # 中等功能，覆盖 18 类场景
            "high": 25,      # 复杂功能，覆盖全部 25 类场景
        }

        return complexity_map.get(complexity, 15)

    def _filter_existing_features(self, features: List[Dict]) -> List[Dict]:
        """增量模式：过滤已存在的功能"""
        if not os.path.exists(self.history_path):
            return features

        with open(self.history_path, "r", encoding="utf-8") as f:
            history = json.load(f)

        existing_modules = {
            m["module"] for m in history.get("generated_modules", [])
        }

        filtered = []
        for feature in features:
            if feature["module_name"] not in existing_modules:
                filtered.append(feature)
            else:
                print(f"[SKIP] 模块已存在: {feature['module_name']}")

        return filtered

    def _update_history(self, features: List[Dict], testcases: List[Dict]):
        """更新测试用例历史记录"""
        if not os.path.exists(self.history_path):
            history = {
                "version": "1.0.0",
                "current_index": 0,
                "project_name": self.project_name,
                "last_scan": "",
                "generated_modules": [],
                "scanned_commits": [],
                "scanned_prs": [],
                "scanned_branches": [],
                "file_hashes": {}
            }
        else:
            with open(self.history_path, "r", encoding="utf-8") as f:
                history = json.load(f)

        # 更新基本信息
        history["project_name"] = self.project_name
        history["last_scan"] = datetime.now(timezone.utc).isoformat()

        # 更新编号
        if testcases:
            last_id = testcases[-1].get("测试用例序号", "testcase_000")
            history["current_index"] = int(last_id.replace("testcase_", ""))

        # 记录已扫描的 commit/PR
        if self.commit_sha:
            history.setdefault("scanned_commits", []).append(self.commit_sha)
        if self.pr_number:
            history.setdefault("scanned_prs", []).append(self.pr_number)
        if self.branch:
            history.setdefault("scanned_branches", []).append(self.branch)

        # 记录生成的模块
        testcase_ids = [tc["测试用例序号"] for tc in testcases]
        for feature in features:
            history.setdefault("generated_modules", []).append({
                "module": feature["module_name"],
                "testcase_count": feature["estimated_testcase_count"],
                "testcase_ids": testcase_ids if not history["generated_modules"] else [],
                "source_commit": self.commit_sha or "",
                "generated_at": datetime.now(timezone.utc).isoformat()
            })

        # 写回文件
        with open(self.history_path, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)

        print(f"[INFO] History 已更新 (current_index={history['current_index']})")

    def cleanup(self):
        """清理临时文件"""
        if self.work_dir and os.path.exists(self.work_dir):
            shutil.rmtree(self.work_dir)
            print(f"[INFO] 已清理临时目录: {self.work_dir}")


def parse_args() -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="GitHub 仓库扫描器 - 自动生成中文测试用例",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s --repo https://github.com/example/helix.git --project-name Helix
  %(prog)s --repo https://github.com/example/helix.git --pr 42 --incremental
  %(prog)s --repo https://github.com/example/helix.git --commit abc123
  %(prog)s --diff ./changes.diff --project-name Helix
        """
    )

    parser.add_argument(
        "--repo", type=str,
        help="GitHub 仓库 URL"
    )
    parser.add_argument(
        "--branch", type=str, default="main",
        help="目标分支 (默认: main)"
    )
    parser.add_argument(
        "--commit", type=str,
        help="目标 Commit SHA"
    )
    parser.add_argument(
        "--pr", type=int,
        help="Pull Request 编号"
    )
    parser.add_argument(
        "--diff", type=str,
        help="自定义 Diff 文件路径"
    )
    parser.add_argument(
        "--project-name", type=str, required=True,
        help="项目名称 (用于 CSV 文件命名)"
    )
    parser.add_argument(
        "--output-dir", type=str,
        help="输出目录 (默认: 当前目录)"
    )
    parser.add_argument(
        "--incremental", action="store_true", default=True,
        help="启用增量模式 (默认启用)"
    )
    parser.add_argument(
        "--full", action="store_true",
        help="全量重新生成 (禁用增量模式)"
    )
    parser.add_argument(
        "--coverage-level", type=str, choices=["basic", "standard", "full"],
        default="standard",
        help="覆盖级别: basic(10)/standard(18)/full(25) (默认: standard)"
    )

    args = parser.parse_args()

    # 验证参数
    if not args.repo and not args.diff:
        parser.error("必须提供 --repo 或 --diff 参数")

    if args.full:
        args.incremental = False

    return args


def main():
    """主函数"""
    args = parse_args()

    scanner = RepositoryScanner(args)
    try:
        output_path = scanner.run()
        if output_path:
            print(f"\n{'='*60}")
            print(f"✓ 测试用例生成成功!")
            print(f"  输出文件: {output_path}")
            print(f"{'='*60}")
        else:
            print("\n[INFO] 无新增测试用例需要生成")
    except Exception as e:
        print(f"\n[ERROR] 扫描失败: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        scanner.cleanup()


if __name__ == "__main__":
    main()
