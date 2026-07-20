#!/usr/bin/env python3
"""
generate_testcase.py - LLM 调用生成测试用例

职责：
  1. 接收功能描述和上下文信息
  2. 加载 Prompt 模板
  3. 调用 LLM API 生成测试用例
  4. 解析 LLM 返回的 CSV 格式结果
  5. 对结果进行格式校验和清洗

支持的 LLM 后端：
  - OpenAI API (GPT-4, GPT-3.5)
  - Azure OpenAI
  - 本地 LLM (兼容 OpenAI 接口)

环境变量：
  - OPENAI_API_KEY: OpenAI API 密钥
  - OPENAI_API_BASE: OpenAI API 基础 URL (可选)
  - LLM_MODEL: 模型名称 (默认: gpt-4)
"""

import csv
import io
import json
import os
import re
import time
from typing import List, Dict, Optional


class TestCaseGenerator:
    """测试用例生成器 - 调用 LLM 生成中文测试用例"""

    # 25 类测试场景定义
    COVERAGE_SCENARIOS = [
        {"name": "正向功能", "priority": "P0", "description": "基本功能正常流程测试"},
        {"name": "反向功能", "priority": "P1", "description": "异常输入/错误操作测试"},
        {"name": "空值测试", "priority": "P1", "description": "必填字段为空值测试"},
        {"name": "Null值测试", "priority": "P1", "description": "字段值为null的测试"},
        {"name": "边界值测试", "priority": "P1", "description": "临界值（0, 1, max, max+1）测试"},
        {"name": "最大长度测试", "priority": "P3", "description": "输入超过最大长度测试"},
        {"name": "最小长度测试", "priority": "P3", "description": "输入不足最小长度测试"},
        {"name": "特殊字符测试", "priority": "P1", "description": "<>'\"&/| 等特殊字符测试"},
        {"name": "SQL注入测试", "priority": "P0", "description": "' OR '1'='1 等注入测试"},
        {"name": "XSS测试", "priority": "P0", "description": "<script>alert(1)</script> 测试"},
        {"name": "权限测试", "priority": "P0", "description": "无权限/越权操作测试"},
        {"name": "重复提交测试", "priority": "P2", "description": "快速双击/多次点击测试"},
        {"name": "并发测试", "priority": "P2", "description": "多人同时操作测试"},
        {"name": "网络异常测试", "priority": "P2", "description": "断网/弱网环境测试"},
        {"name": "超时测试", "priority": "P2", "description": "接口超时处理测试"},
        {"name": "浏览器兼容测试", "priority": "P3", "description": "Chrome/Firefox/Safari/Edge 测试"},
        {"name": "分辨率测试", "priority": "P3", "description": "1920x1080 / 1366x768 / 375x667 测试"},
        {"name": "国际化测试", "priority": "P4", "description": "中英文切换测试"},
        {"name": "文件格式测试", "priority": "P2", "description": "支持/不支持的文件格式测试"},
        {"name": "文件大小测试", "priority": "P2", "description": "超大文件/空文件测试"},
        {"name": "AI异常返回测试", "priority": "P2", "description": "AI返回格式错误/内容异常测试"},
        {"name": "服务重启测试", "priority": "P3", "description": "操作过程中服务重启测试"},
        {"name": "Token失效测试", "priority": "P1", "description": "Token过期后的行为测试"},
        {"name": "Session过期测试", "priority": "P1", "description": "Session超时后的行为测试"},
        {"name": "回归测试", "priority": "P4", "description": "修改后关联功能正常性测试"},
    ]

    def __init__(self, prompt_template_dir: str = None):
        """
        初始化生成器

        Args:
            prompt_template_dir: Prompt 模板目录路径
        """
        self.prompt_template_dir = prompt_template_dir
        self.api_key = os.environ.get("OPENAI_API_KEY", "")
        self.api_base = os.environ.get("OPENAI_API_BASE", "https://api.openai.com/v1")
        self.model = os.environ.get("LLM_MODEL", "gpt-4")

        # 加载系统提示
        self.system_prompt = self._load_system_prompt()

    def generate(
        self,
        feature: Dict,
        allocated_ids: List[str],
        coverage_level: str = "standard"
    ) -> List[Dict]:
        """
        为单个功能生成测试用例

        Args:
            feature: 功能描述字典
            allocated_ids: 分配的测试用例编号列表
            coverage_level: 覆盖级别

        Returns:
            测试用例列表（每项为字典）
        """
        feature_name = feature.get("feature_name", "未命名功能")
        module_name = feature.get("module_name", "通用")
        description = feature.get("feature_description", "")
        code_context = feature.get("code_context", "")
        estimated_count = feature.get("estimated_testcase_count", 15)

        # 根据覆盖级别确定场景数量
        scenario_count = self._get_scenario_count(coverage_level, estimated_count)
        scenarios = self.COVERAGE_SCENARIOS[:scenario_count]

        testcases = []

        for i, scenario in enumerate(scenarios):
            if i >= len(allocated_ids):
                break

            tc_id = allocated_ids[i]
            testcase = self._generate_single_testcase(
                tc_id=tc_id,
                module_name=module_name,
                feature_name=feature_name,
                scenario=scenario,
                description=description,
                code_context=code_context
            )
            if testcase:
                testcases.append(testcase)

        return testcases

    def _generate_single_testcase(
        self,
        tc_id: str,
        module_name: str,
        feature_name: str,
        scenario: Dict,
        description: str,
        code_context: str
    ) -> Optional[Dict]:
        """
        生成单个测试用例

        优先调用 LLM，如果 LLM 不可用则使用规则生成
        """
        if self.api_key:
            return self._llm_generate(
                tc_id, module_name, feature_name, scenario, description, code_context
            )
        else:
            return self._rule_based_generate(
                tc_id, module_name, feature_name, scenario, description
            )

    def _llm_generate(
        self,
        tc_id: str,
        module_name: str,
        feature_name: str,
        scenario: Dict,
        description: str,
        code_context: str
    ) -> Optional[Dict]:
        """使用 LLM 生成测试用例"""
        try:
            import openai
            client = openai.OpenAI(api_key=self.api_key, base_url=self.api_base)

            user_prompt = self._build_generation_prompt(
                tc_id, module_name, feature_name, scenario, description, code_context
            )

            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=500
            )

            content = response.choices[0].message.content.strip()
            return self._parse_llm_response(content, tc_id, module_name, scenario)

        except Exception as e:
            print(f"[WARN] LLM 调用失败 ({scenario['name']}): {e}")
            # Fallback 到规则生成
            return self._rule_based_generate(
                tc_id, module_name, feature_name, scenario, description
            )

    def _rule_based_generate(
        self,
        tc_id: str,
        module_name: str,
        feature_name: str,
        scenario: Dict,
        description: str
    ) -> Dict:
        """基于规则生成测试用例（无 LLM 时的回退方案）"""
        title = self._generate_title(feature_name, scenario["name"])
        steps = self._generate_steps(feature_name, scenario["name"])
        expected = self._generate_expected_results(feature_name, scenario["name"])

        return {
            "测试用例序号": tc_id,
            "模块": module_name,
            "测试点": scenario["name"],
            "测试用例标题": title,
            "优先级": scenario["priority"],
            "操作步骤": steps,
            "预期结果": expected,
            "最终结果": "",
            "备注": f"规则生成 - {scenario['description']}",
            "测试人": ""
        }

    def _generate_title(self, feature_name: str, scenario_name: str) -> str:
        """生成测试标题"""
        # 清理功能名
        clean_name = re.sub(r'^(新增|修改|删除)[：:]?\s*', '', feature_name)
        clean_name = clean_name[:15]  # 限制长度

        # 组合标题
        title_templates = {
            "正向功能": f"{clean_name}成功",
            "反向功能": f"{clean_name}失败提示",
            "空值测试": f"{clean_name}空值校验",
            "Null值测试": f"{clean_name}Null值处理",
            "边界值测试": f"{clean_name}边界值验证",
            "最大长度测试": f"{clean_name}超长输入",
            "最小长度测试": f"{clean_name}输入不足",
            "特殊字符测试": f"{clean_name}特殊字符处理",
            "SQL注入测试": f"{clean_name}SQL注入防护",
            "XSS测试": f"{clean_name}XSS攻击防护",
            "权限测试": f"{clean_name}权限校验",
            "重复提交测试": f"{clean_name}重复提交防护",
            "并发测试": f"{clean_name}并发操作",
            "网络异常测试": f"{clean_name}网络异常处理",
            "超时测试": f"{clean_name}超时处理",
            "浏览器兼容测试": f"{clean_name}浏览器兼容性",
            "分辨率测试": f"{clean_name}分辨率适配",
            "国际化测试": f"{clean_name}国际化展示",
            "文件格式测试": f"{clean_name}文件格式校验",
            "文件大小测试": f"{clean_name}文件大小限制",
            "AI异常返回测试": f"{clean_name}AI异常处理",
            "服务重启测试": f"{clean_name}服务重启恢复",
            "Token失效测试": f"{clean_name}Token失效处理",
            "Session过期测试": f"{clean_name}Session过期处理",
            "回归测试": f"{clean_name}回归验证",
        }

        return title_templates.get(scenario_name, f"{clean_name}{scenario_name}")

    def _generate_steps(self, feature_name: str, scenario_name: str) -> str:
        """生成操作步骤"""
        steps_map = {
            "正向功能": [
                "1 进入功能页面",
                "2 输入有效数据",
                "3 点击提交/确认",
                "4 查看操作结果"
            ],
            "反向功能": [
                "1 进入功能页面",
                "2 输入无效数据",
                "3 点击提交/确认",
                "4 查看错误提示"
            ],
            "空值测试": [
                "1 进入功能页面",
                "2 不填写必填项",
                "3 点击提交",
                "4 查看校验提示"
            ],
            "边界值测试": [
                "1 进入功能页面",
                "2 输入边界值数据",
                "3 点击提交",
                "4 查看处理结果"
            ],
            "权限测试": [
                "1 使用无权限账号登录",
                "2 尝试访问功能",
                "3 查看权限拦截"
            ],
            "并发测试": [
                "1 打开两个浏览器窗口",
                "2 同时执行相同操作",
                "3 查看数据处理结果"
            ],
            "超时测试": [
                "1 触发需要长时间处理的操作",
                "2 等待超时",
                "3 查看超时提示"
            ],
            "Token失效测试": [
                "1 使用过期Token发起请求",
                "2 查看响应结果",
                "3 确认重定向到登录页"
            ],
        }

        steps = steps_map.get(scenario_name, [
            "1 进入功能页面",
            "2 执行相关操作",
            "3 查看结果"
        ])

        return "\n".join(steps)

    def _generate_expected_results(self, feature_name: str, scenario_name: str) -> str:
        """生成预期结果"""
        expected_map = {
            "正向功能": [
                "操作执行成功",
                "页面显示成功提示信息",
                "数据正确保存到数据库",
                "接口返回状态码200"
            ],
            "反向功能": [
                "操作被阻止",
                "页面显示具体错误提示信息",
                "数据未被保存",
                "接口返回相应错误状态码"
            ],
            "空值测试": [
                "页面显示必填项校验提示",
                "数据未被提交",
                "输入框标红或显示错误图标"
            ],
            "边界值测试": [
                "临界值以内的数据正常处理",
                "超出临界值的数据被正确拦截",
                "返回明确的提示信息"
            ],
            "权限测试": [
                "无权限用户被拦截",
                "显示权限不足提示",
                "接口返回403状态码"
            ],
            "超时测试": [
                "超过设定时间后显示超时提示",
                "正在进行的操作被取消",
                "可重新发起操作"
            ],
            "Token失效测试": [
                "接口返回401状态码",
                "前端自动跳转到登录页面",
                "清除LocalStorage中的Token"
            ],
        }

        results = expected_map.get(scenario_name, [
            "操作结果符合预期",
            "页面显示相应提示",
            "数据处理正确"
        ])

        return "\n".join(results)

    def _load_system_prompt(self) -> str:
        """加载系统 Prompt"""
        if self.prompt_template_dir:
            prompt_file = os.path.join(self.prompt_template_dir, "prompt.md")
            if os.path.exists(prompt_file):
                with open(prompt_file, "r", encoding="utf-8") as f:
                    content = f.read()
                    # 提取系统角色 Prompt 部分
                    match = re.search(
                        r'## 1\. 系统角色 Prompt\s*\n```\n(.*?)```',
                        content, re.DOTALL
                    )
                    if match:
                        return match.group(1).strip()

        # 默认系统 Prompt
        return """你是一名资深软件测试架构师，拥有 10 年以上测试经验。
你精通前端测试、后端测试、安全测试、性能测试、AI 应用测试。
你的任务是按照严格规范生成中文测试用例。
输出要求：始终使用中文，标题简洁明确，操作步骤清晰，预期结果具体。"""

    def _build_generation_prompt(
        self,
        tc_id: str,
        module_name: str,
        feature_name: str,
        scenario: Dict,
        description: str,
        code_context: str
    ) -> str:
        """构建生成 Prompt"""
        prompt = f"""请为以下功能生成一个中文测试用例。

功能名称：{feature_name}
所属模块：{module_name}
功能描述：{description}
测试场景：{scenario['name']} - {scenario['description']}
优先级：{scenario['priority']}
用例编号：{tc_id}

相关代码上下文：
{code_context[:500] if code_context else '无'}

请输出一行 CSV 格式的数据（不含表头）：
{tc_id},{module_name},{scenario['name']},<标题>,{scenario['priority']},<操作步骤(用\\n分隔)>,<预期结果(用\\n分隔)>,,,

要求：
1. 标题 8-25 字符，中文，包含操作和结果
2. 操作步骤短小清晰，序号用数字
3. 预期结果具体明确，不能写"正常""成功"等模糊词"""
        return prompt

    def _parse_llm_response(
        self,
        content: str,
        tc_id: str,
        module_name: str,
        scenario: Dict
    ) -> Optional[Dict]:
        """解析 LLM 返回的 CSV 内容"""
        if not content:
            return None

        # 尝试解析 CSV 行
        try:
            reader = csv.reader(io.StringIO(content))
            for row in reader:
                if row and row[0] == tc_id:
                    return {
                        "测试用例序号": row[0] if len(row) > 0 else tc_id,
                        "模块": row[1] if len(row) > 1 else module_name,
                        "测试点": row[2] if len(row) > 2 else scenario["name"],
                        "测试用例标题": row[3] if len(row) > 3 else "",
                        "优先级": row[4] if len(row) > 4 else scenario["priority"],
                        "操作步骤": row[5] if len(row) > 5 else "",
                        "预期结果": row[6] if len(row) > 6 else "",
                        "最终结果": row[7] if len(row) > 7 else "",
                        "备注": row[8] if len(row) > 8 else "",
                        "测试人": row[9] if len(row) > 9 else ""
                    }
        except Exception:
            pass

        return None

    def _get_scenario_count(self, coverage_level: str, estimated_count: int) -> int:
        """根据覆盖级别确定场景数量"""
        level_map = {
            "basic": min(10, estimated_count),
            "standard": min(18, estimated_count),
            "full": min(25, estimated_count)
        }
        return level_map.get(coverage_level, 18)

    def validate_testcase(self, testcase: Dict) -> List[str]:
        """校验测试用例格式"""
        errors = []

        required_fields = ["测试用例序号", "模块", "测试点", "测试用例标题", "优先级", "操作步骤", "预期结果"]
        for field in required_fields:
            if not testcase.get(field):
                errors.append(f"缺少必填字段: {field}")

        # 校验编号格式
        tc_id = testcase.get("测试用例序号", "")
        if not re.match(r'^testcase_\d{3}$', tc_id):
            errors.append(f"编号格式错误: {tc_id}")

        # 校验标题
        title = testcase.get("测试用例标题", "")
        if title in ["测试登录", "功能验证", "测试", ""]:
            errors.append(f"标题不符合规范: {title}")
        if len(title) < 4 or len(title) > 30:
            errors.append(f"标题长度不合适 ({len(title)}): {title}")

        # 校验预期结果
        expected = testcase.get("预期结果", "")
        vague_words = ["正常", "成功", "正确"]
        for word in vague_words:
            if expected.strip() == word:
                errors.append(f"预期结果过于模糊: {expected}")
                break

        # 校验优先级
        priority = testcase.get("优先级", "")
        if priority not in ["P0", "P1", "P2", "P3", "P4"]:
            errors.append(f"优先级不合法: {priority}")

        return errors


# 命令行独立运行
if __name__ == "__main__":
    import sys

    generator = TestCaseGenerator()

    # 测试规则生成
    test_feature = {
        "feature_name": "登录",
        "module_name": "登录",
        "feature_description": "用户登录功能",
        "code_context": "",
        "estimated_testcase_count": 15
    }

    test_ids = [f"testcase_{i:03d}" for i in range(1, 26)]

    testcases = generator.generate(
        feature=test_feature,
        allocated_ids=test_ids,
        coverage_level="full"
    )

    for tc in testcases:
        print(json.dumps(tc, ensure_ascii=False))
