---
name: github-web-testcase-generator
description: Use when Codex 需要根据 GitHub/code 仓库、PR diff 或本地 git diff 增量生成 YAML Web 自动化测试用例，包括冒烟测试、全量测试、仓库扫描、已有用例去重，以及 Repository secrets 安全输入。
---

# GitHub Web 测试用例生成器

## 概览

根据仓库上下文和 PR diff 生成 Codex 可执行的自然语言 Web 自动化测试用例。默认只输出增量 YAML 用例；除非用户明确要求重写或重排已有用例，不要改写已有用例。

## 必读参考

生成测试用例前先阅读这些文件：

- `references/testcase-yaml-schema.md`：YAML 必填字段、编号规则和示例。
- `references/coverage-and-dedup-rules.md`：冒烟测试、全量测试、场景覆盖和去重规则。
- `references/repository-secrets.md`：GitHub Repository secrets 和隐私安全规则。

## 工作流

1. 识别生成模式：
   - 用户说“冒烟测试、主流程、核心流程、smoke、happy path”时，只生成核心主流程和高风险路径用例。
   - 用户说“全量测试、完整、全面、full、complete、comprehensive”时，生成受影响范围内的完整用例。
   - 如果模式不明确，先问一个简短澄清问题。
2. 扫描仓库上下文：
   - 使用 `rg --files` 查找前端路由、页面、组件、表单、按钮、弹窗、菜单、API client、鉴权/权限逻辑、状态流转、E2E 配置和已有 YAML 用例。
   - 优先扫描仓库的 `web/` 目录；重点查看 `web/src/app`、`web/src/pages`、`web/src/components`、`web/src/service`、`web/src/hooks`、`web/src/stores`、`web/src/types`、`web/src/config`。
   - 有 GitHub PR 上下文时使用 PR diff 或 `gh pr diff`；否则查看 `git diff`、`git diff --staged`、`git log --name-status` 和当前分支近期变更。
   - 不要编造代码、文案、页面或业务行为；必须能从代码、测试、文档、路由、UI 文案或 diff 推断。
3. 从 `web/` 元素推导可执行步骤：
   - 优先提取真实可见元素：按钮文本、链接文本、菜单项、tab 文案、弹窗标题、表单 label、placeholder、aria-label、alt、toast 文案、状态标签、空态文案。
   - 优先用真实路由：例如 `/home`、`/writing`、`/plots/:id`，不要凭空命名页面。
   - 优先使用用户会看到的自然语言动作：`点击创建任务`、`选择综述任务类型`、`点击任务分析`、`点击资料`、`点击下载`、`等待任务状态变为已完成`。
   - 表单步骤必须来自真实字段或可推断字段；如果字段由后端配置动态生成，步骤要写成“填写测试环境预置的必填项”，并在预期结果里说明需要测试数据 fixture。
   - 预期结果必须来自页面可观察状态：可见文案、URL 跳转、按钮状态、弹窗出现、toast、列表项、状态标签、下载动作、错误提示或空态。
4. 查找已有测试用例：
   - 搜索文件名或目录包含 `testcase`、`test-case`、`e2e`、`web`、`automation`、`测试用例` 的 YAML 文件。
   - 读取已有用例，找出最大的 `testcase_NNN` 编号。
   - 新用例从下一个编号开始，编号必须连续。
5. 推导受影响模块：
   - 将变更文件映射到页面、路由、组件、表单、弹窗、服务调用和业务模块。
   - 追踪相关 API 调用、校验规则、按钮、权限分支、loading/error/empty 状态和状态流转。
   - 如果共享组件、schema、API client、auth guard 或状态工具变更，要包含间接受影响的用户流程。
6. 只生成缺失用例：
   - 按模块、测试点、标题、步骤、预期结果、场景类型比较候选用例和已有用例。
   - 已有相同或等价覆盖时跳过。
   - 只为新功能、变更行为和缺失覆盖生成新用例。
7. 输出前自检 YAML：
   - 每条用例包含所有必填字段。
   - 新用例编号连续。
   - `最终结果` 默认为 `未执行`，除非用户提供真实执行结果。
   - 生成批次包含正向、反向、为空、边界值、极端场景。
   - 不包含任何明文 URL、账号、密码、token、cookie 或 API key。

## 输出约定

返回顶层字段为 `testcases` 的 YAML。字段名必须使用 `references/testcase-yaml-schema.md` 中定义的中文字段。

如果用户要求写入文件，则写入用户指定路径或项目已有测试用例目录；否则直接在回复中输出 YAML。

## 隐私约定

不要把项目密钥写入生成的测试用例、文件、日志、注释或示例。只能引用 secret 名称，例如 `TEST_BASE_URL`、`TEST_USERNAME`、`TEST_PASSWORD`、`TEST_OTP_SECRET`、`TEST_API_TOKEN`；并提醒用户在 GitHub Repository secrets 中人工配置。

## 常见错误

- 不要重复生成已有测试用例。
- 不要跳号或重新从 `testcase_001` 编号。
- 不要只生成正向用例。
- 不要把预期结果写成模糊描述；必须是可验证断言。
- 不要泄露明文测试地址、账号、密码、token、cookie 或 API key。
- 不要在没有读取仓库上下文、`web/` 元素和 PR/local diff 前凭空生成用例。
