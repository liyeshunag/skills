#!/usr/bin/env python3
"""
parse_diff.py - Git Diff 解析器

职责：
  1. 解析 unified diff 格式的 Git Diff
  2. 识别变更类型：新增文件(new)、修改文件(modified)、删除文件(deleted)、重命名(renamed)
  3. 提取代码变更片段 (hunk)
  4. 推断功能点、模块名、复杂度
  5. 输出结构化的变更列表

输入：Git Diff 文本（unified diff 格式）
输出：List[Dict] 结构化变更列表

  每条变更记录：
  {
    "type": "new" | "modified" | "deleted" | "renamed",
    "file_path": "src/pages/login/index.tsx",
    "module_name": "登录",
    "feature_name": "新增密码强度校验",
    "description": "登录页面新增了密码强度实时校验功能",
    "complexity": "low" | "medium" | "high",
    "code_snippet": "...",
    "added_lines": 45,
    "deleted_lines": 10,
    "hunks": [...]
  }
"""

import re
from typing import List, Dict, Optional, Tuple
from pathlib import Path


class DiffParser:
    """Git Diff 解析器"""

    # 文件路径 → 模块名映射模式
    MODULE_PATTERNS = [
        # 前端页面路由
        (r"src/pages/(\w+)", lambda m: m.group(1)),
        (r"src/views/(\w+)", lambda m: m.group(1)),
        (r"pages/(\w+)", lambda m: m.group(1)),
        # 组件
        (r"src/components/(\w+)", lambda m: m.group(1)),
        (r"components/(\w+)", lambda m: m.group(1)),
        # API 路由
        (r"src/api/(\w+)", lambda m: m.group(1)),
        (r"api/(\w+)/", lambda m: m.group(1)),
        (r"routes/(\w+)", lambda m: m.group(1)),
        # 数据库迁移
        (r"migrations/.*", lambda m: "数据库"),
        # 配置文件
        (r"config/(\w+)", lambda m: m.group(1)),
        (r"\.env", lambda m: "配置"),
        # 模型
        (r"models/(\w+)", lambda m: m.group(1)),
        (r"src/models/(\w+)", lambda m: m.group(1)),
    ]

    # 代码特征 → 功能类型映射
    FEATURE_PATTERNS = [
        # 新增页面
        (r"(?:Route|route)\s+.*path\s*=\s*['\"]([^'\"]+)", "新增页面路由"),
        (r"(?:createBrowserRouter|createRouter)", "新增路由配置"),
        # 新增接口
        (r"(?:@app\.(?:post|get|put|delete|patch)|@router\.(?:post|get|put|delete|patch))\s*\(\s*['\"]([^'\"]+)", "新增API接口"),
        (r"(?:app\.(?:post|get|put|delete|patch)\s*\(\s*['\"]([^'\"]+)", "新增API接口"),
        (r"(?:router\.(?:post|get|put|delete|patch)\s*\(\s*['\"]([^'\"]+)", "新增API接口"),
        (r"(?:fetch|axios\.(?:post|get|put|delete))\s*\(\s*['\"]([^'\"]+)", "新增接口调用"),
        # 新增组件
        (r"(?:export\s+(?:default\s+)?(?:function|class)\s+(\w+))", "新增组件/类"),
        (r"const\s+\w+\s*=\s*(?:styled\.\w+|memo)", "新增样式组件"),
        # 新增按钮/交互
        (r"<(?:Button|button)[^>]*onClick", "新增按钮交互"),
        (r"<(?:Button|button)[^>]*>", "新增按钮"),
        # 新增表单
        (r"<(?:input|Input|select|Select|Form)", "新增表单元素"),
        (r"useForm|Form\.useForm", "新增表单"),
        # 新增弹窗
        (r"<(?:Modal|Dialog|Drawer)", "新增弹窗"),
        # 新增权限
        (r"(?:role|permission|auth|can\s*\(|hasPermission)", "新增权限逻辑"),
        # 新增数据库字段
        (r"(?:ALTER\s+TABLE\s+.*ADD\s+COLUMN|add_column|AddColumn)", "新增数据库字段"),
        # 新增配置
        (r"(?:config|Config|setting|Setting)\[", "新增配置项"),
        # 新增状态管理
        (r"(?:useState|useReducer|createStore|atom\()", "新增状态管理"),
        # AI 相关
        (r"(?:AI|LLM|GPT|prompt|embedding|生成|generate)", "新增AI功能"),
    ]

    def __init__(self):
        self.complexity_keywords = {
            "high": [
                r"transaction", r"payment", r"auth", r"permission",
                r"encrypt", r"decrypt", r"oauth", r"workflow",
                r"async", r"concurrent", r"queue", r"lock",
                r"state\s+machine", r"状态机"
            ],
            "low": [
                r"text", r"label", r"title", r"icon",
                r"style", r"color", r"font", r"margin",
                r"padding", r"className"
            ]
        }

    def parse(self, diff_content: str) -> List[Dict]:
        """
        解析 Git Diff 内容

        Args:
            diff_content: unified diff 格式的文本

        Returns:
            结构化的变更列表
        """
        if not diff_content.strip():
            return []

        # 按文件切分 Diff
        file_diffs = self._split_by_file(diff_content)
        changes = []

        for file_diff in file_diffs:
            change = self._parse_file_diff(file_diff)
            if change:
                changes.append(change)

        return changes

    def _split_by_file(self, diff_content: str) -> List[str]:
        """按文件切分 Diff 内容"""
        # 匹配 diff --git 或 --- a/ 和 +++ b/ 模式
        parts = re.split(r'\n(?=diff --git )', diff_content)
        return [p.strip() for p in parts if p.strip()]

    def _parse_file_diff(self, file_diff: str) -> Optional[Dict]:
        """解析单个文件的 Diff"""
        lines = file_diff.split('\n')

        # 提取文件路径
        file_path = self._extract_file_path(lines)
        if not file_path:
            return None

        # 判断变更类型
        change_type = self._determine_change_type(lines)

        # 统计变更行数
        added_lines = sum(1 for line in lines if line.startswith('+') and not line.startswith('+++'))
        deleted_lines = sum(1 for line in lines if line.startswith('-') and not line.startswith('---'))

        # 提取代码片段（变更的代码行）
        code_snippet = self._extract_code_snippet(lines)

        # 提取 hunks
        hunks = self._extract_hunks(lines)

        # 推断模块名
        module_name = self._infer_module_name(file_path)

        # 推断功能名
        feature_name = self._infer_feature_name(code_snippet, file_path)

        # 推断复杂度
        complexity = self._infer_complexity(code_snippet, added_lines, deleted_lines)

        # 推断描述
        description = self._infer_description(
            change_type, module_name, feature_name, added_lines, deleted_lines
        )

        return {
            "type": change_type,
            "file_path": file_path,
            "module_name": module_name,
            "feature_name": feature_name,
            "description": description,
            "complexity": complexity,
            "code_snippet": code_snippet,
            "added_lines": added_lines,
            "deleted_lines": deleted_lines,
            "hunks": hunks
        }

    def _extract_file_path(self, lines: List[str]) -> Optional[str]:
        """提取变更文件路径"""
        for line in lines:
            # 匹配 +++ b/path/to/file
            match = re.match(r'\+\+\+\s+b/(.+)', line)
            if match:
                return match.group(1)
            # 匹配 diff --git a/path b/path
            match = re.match(r'diff --git a/(.+) b/(.+)', line)
            if match:
                return match.group(2) if match.group(2) != '/dev/null' else match.group(1)
        return None

    def _determine_change_type(self, lines: List[str]) -> str:
        """判断变更类型"""
        file_diff_text = '\n'.join(lines)

        if 'new file mode' in file_diff_text:
            return "new"
        if 'deleted file mode' in file_diff_text:
            return "deleted"
        if 'rename from' in file_diff_text or 'rename to' in file_diff_text:
            return "renamed"

        # 检查是否同时有新增和删除行（修改）
        has_additions = any(l.startswith('+') and not l.startswith('+++') for l in lines)
        has_deletions = any(l.startswith('-') and not l.startswith('---') for l in lines)

        if has_additions or has_deletions:
            return "modified"

        return "unknown"

    def _extract_code_snippet(self, lines: List[str]) -> str:
        """提取代码变更片段"""
        code_lines = []
        in_hunk = False

        for line in lines:
            if line.startswith('@@'):
                in_hunk = True
                continue
            if in_hunk:
                if line.startswith('+') or line.startswith('-') or line.startswith(' '):
                    # 去除 diff 前缀，保留代码
                    code_lines.append(line[1:])
                elif line.startswith('diff --git'):
                    break

        snippet = '\n'.join(code_lines[:80])  # 限制 80 行
        return snippet

    def _extract_hunks(self, lines: List[str]) -> List[Dict]:
        """提取 diff hunks"""
        hunks = []
        current_hunk = None

        for line in lines:
            hunk_match = re.match(
                r'@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@\s*(.*)', line
            )
            if hunk_match:
                if current_hunk:
                    hunks.append(current_hunk)
                current_hunk = {
                    "old_start": int(hunk_match.group(1)),
                    "old_count": int(hunk_match.group(2)) if hunk_match.group(2) else 1,
                    "new_start": int(hunk_match.group(3)),
                    "new_count": int(hunk_match.group(4)) if hunk_match.group(4) else 1,
                    "context": hunk_match.group(5) or "",
                    "lines": []
                }
            elif current_hunk is not None:
                current_hunk["lines"].append(line)

        if current_hunk:
            hunks.append(current_hunk)

        return hunks

    def _infer_module_name(self, file_path: str) -> str:
        """根据文件路径推断模块名"""
        for pattern, resolver in self.MODULE_PATTERNS:
            match = re.search(pattern, file_path)
            if match:
                try:
                    name = resolver(match)
                    # 简单的中文映射
                    return self._to_chinese_module_name(name)
                except Exception:
                    pass

        # 从路径中提取目录名
        parts = Path(file_path).parts
        if len(parts) >= 2:
            return self._to_chinese_module_name(parts[-2])

        return "通用"

    def _to_chinese_module_name(self, name: str) -> str:
        """将英文模块名映射为中文"""
        mapping = {
            "login": "登录",
            "register": "注册",
            "user": "用户管理",
            "profile": "个人资料",
            "dashboard": "仪表盘",
            "settings": "设置",
            "admin": "管理员",
            "order": "订单管理",
            "product": "商品管理",
            "payment": "支付",
            "upload": "文件上传",
            "search": "搜索",
            "notification": "通知",
            "message": "消息",
            "report": "报表",
            "analytics": "数据分析",
            "auth": "认证授权",
            "api": "API接口",
            "config": "配置管理",
            "database": "数据库",
            "migrations": "数据库迁移",
            "models": "数据模型",
            "components": "组件",
            "pages": "页面",
            "utils": "工具",
            "services": "服务",
            "hooks": "钩子",
            "store": "状态管理",
            "router": "路由",
        }
        return mapping.get(name.lower(), name)

    def _infer_feature_name(self, code_snippet: str, file_path: str) -> str:
        """推断功能名称"""
        for pattern, feature_type in self.FEATURE_PATTERNS:
            match = re.search(pattern, code_snippet, re.IGNORECASE)
            if match:
                detail = match.group(1) if match.lastindex else ""
                if detail:
                    return f"{feature_type}: {detail}"
                return feature_type

        # 从文件路径推断
        file_name = Path(file_path).stem
        return f"修改: {file_name}"

    def _infer_complexity(self, code_snippet: str, added_lines: int, deleted_lines: int) -> str:
        """推断功能复杂度"""
        # 基于变更行数
        total_changes = added_lines + deleted_lines
        if total_changes > 200:
            return "high"
        if total_changes > 50:
            return "medium"

        # 基于关键词
        for keyword in self.complexity_keywords["high"]:
            if re.search(keyword, code_snippet, re.IGNORECASE):
                return "high"

        for keyword in self.complexity_keywords["low"]:
            if re.search(keyword, code_snippet, re.IGNORECASE):
                return "low"

        return "medium"

    def _infer_description(
        self,
        change_type: str,
        module_name: str,
        feature_name: str,
        added_lines: int,
        deleted_lines: int
    ) -> str:
        """推断变更描述"""
        type_map = {
            "new": f"新增{module_name}模块",
            "modified": f"修改{module_name}模块",
            "deleted": f"删除{module_name}模块",
            "renamed": f"重命名{module_name}模块",
            "unknown": f"变更{module_name}模块"
        }

        base_desc = type_map.get(change_type, f"变更{module_name}模块")
        return f"{base_desc}：{feature_name}（+{added_lines} -{deleted_lines}行）"

    def get_file_list(self, changes: List[Dict]) -> List[str]:
        """从变更列表中提取文件路径列表"""
        return [change["file_path"] for change in changes]

    def get_new_files(self, changes: List[Dict]) -> List[str]:
        """获取新增文件列表"""
        return [c["file_path"] for c in changes if c["type"] == "new"]

    def get_modified_files(self, changes: List[Dict]) -> List[str]:
        """获取修改文件列表"""
        return [c["file_path"] for c in changes if c["type"] == "modified"]

    def get_summary(self, changes: List[Dict]) -> Dict:
        """生成变更摘要"""
        return {
            "total_files": len(changes),
            "new_files": sum(1 for c in changes if c["type"] == "new"),
            "modified_files": sum(1 for c in changes if c["type"] == "modified"),
            "deleted_files": sum(1 for c in changes if c["type"] == "deleted"),
            "renamed_files": sum(1 for c in changes if c["type"] == "renamed"),
            "total_added_lines": sum(c["added_lines"] for c in changes),
            "total_deleted_lines": sum(c["deleted_lines"] for c in changes),
            "modules_affected": list(set(c["module_name"] for c in changes)),
            "high_complexity_changes": [
                c["feature_name"] for c in changes if c["complexity"] == "high"
            ]
        }


# 命令行独立运行
if __name__ == "__main__":
    import sys
    import json

    if len(sys.argv) > 1:
        with open(sys.argv[1], "r", encoding="utf-8") as f:
            diff_content = f.read()
    else:
        diff_content = sys.stdin.read()

    parser = DiffParser()
    changes = parser.parse(diff_content)
    summary = parser.get_summary(changes)

    print(json.dumps({
        "changes": changes,
        "summary": summary
    }, ensure_ascii=False, indent=2))
