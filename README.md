# Codex Skills

这个仓库用于维护个人 Codex Skills，重点沉淀 AI 测试、Web 自动化测试用例生成、仓库扫描和安全测试数据约束等可复用能力。

## Skills 列表

### github-web-testcase-generator

根据 GitHub 仓库、本地代码仓库、PR diff 或本地 git diff，生成 Codex 可执行的自然语言 Web 自动化测试用例，输出格式为 YAML。

适用场景：

- 扫描仓库和 PR diff 生成主流程冒烟测试用例
- 扫描仓库和 PR diff 生成全量测试用例
- 只为当前 PR 新增功能生成测试用例
- 基于已有测试用例增量补充缺失用例
- 从真实 Web 页面元素、路由、组件、表单、按钮、弹窗、状态流转和 API 调用推导测试步骤

能力要点：

- 支持冒烟测试模式和全量测试模式
- 输出固定中文字段的 YAML 测试用例
- 自动检查已有测试用例，避免重复生成等价用例
- 测试用例编号使用 `testcase_001`、`testcase_002` 并连续递增
- 覆盖正向、反向、为空、边界值、极端场景
- 优先依据仓库 `web/` 目录中的真实元素生成自然语言操作步骤和断言
- 不允许在测试用例中写入明文测试网址、账号、密码、Token、Cookie 或 API Key

## 目录结构

```text
github-web-testcase-generator/
  SKILL.md
  agents/
    openai.yaml
  references/
    coverage-and-dedup-rules.md
    repository-secrets.md
    testcase-yaml-schema.md
```

## 安装方式

可以将仓库中的 Skill 目录复制到本地 Codex skills 目录，例如：

```bash
mkdir -p ~/.codex/skills
cp -R github-web-testcase-generator ~/.codex/skills/
```

如果使用 Codex 的 Skill 安装能力，也可以从 GitHub 仓库安装：

```text
安装 git@github.com:liyeshunag/skills.git 中的 github-web-testcase-generator
```

## 调用示例

生成主流程冒烟测试用例：

```text
使用 github-web-testcase-generator，扫描当前仓库和 PR diff，生成主流程冒烟测试用例，输出 YAML。
```

生成全量测试用例：

```text
使用 github-web-testcase-generator，扫描当前仓库和 PR diff，生成全量测试用例，另起一个 YAML 文件。
```

只为当前 PR 新增功能补充用例：

```text
使用 github-web-testcase-generator，只为当前 PR 新增功能生成测试用例。
```

基于已有测试用例增量补充：

```text
使用 github-web-testcase-generator，基于已有测试用例增量补充缺失用例。
```

## YAML 输出字段

每条测试用例固定包含以下字段：

- `测试用例序号`
- `模块`
- `测试点`
- `测试用例标题`
- `优先级`
- `操作步骤`
- `预期结果`
- `最终结果`
- `测试人`

示例：

```yaml
testcases:
- 测试用例序号: testcase_001
  模块: 登录
  测试点: 用户使用正确账号密码登录
  测试用例标题: 正确账号密码登录成功
  优先级: P0
  操作步骤:
  - 打开测试网址，测试网址从 TEST_BASE_URL 获取
  - 输入测试账号，测试账号从 TEST_USERNAME 获取
  - 输入测试密码，测试密码从 TEST_PASSWORD 获取
  - 点击登录按钮
  预期结果:
  - 页面跳转到首页或工作台
  - 页面展示当前登录用户信息
  - 不出现登录失败提示
  最终结果: 未执行
  测试人: Codex
```

## 安全约束

测试环境中的敏感信息必须通过 GitHub Repository secrets 或运行时环境变量注入。不要把以下内容写入仓库、测试用例、README、日志或示例文件：

- 测试网址真实值
- 测试账号
- 测试密码
- Token
- Cookie
- API Key
- OTP seed 或验证码绕过配置

推荐的 secret 名称：

- `TEST_BASE_URL`
- `TEST_USERNAME`
- `TEST_PASSWORD`
- `TEST_USER_EMAIL`
- `TEST_USER_PASSWORD`
- `TEST_LIMITED_EMAIL`
- `TEST_LIMITED_PASSWORD`
- `TEST_OTP_SECRET`
- `TEST_API_TOKEN`

GitHub Actions 中可以这样注入：

```yaml
env:
  TEST_BASE_URL: ${{ secrets.TEST_BASE_URL }}
  TEST_USERNAME: ${{ secrets.TEST_USERNAME }}
  TEST_PASSWORD: ${{ secrets.TEST_PASSWORD }}
```

这些 secrets 需要在 GitHub 仓库中人工配置：

```text
Settings -> Secrets and variables -> Actions
```

## 维护建议

- 更新 Skill 后先检查 `SKILL.md` frontmatter 是否只包含 `name` 和 `description`
- `description` 应以 `Use when...` 开头
- 不要提交 `.env`、日志、执行报告、浏览器截图或包含敏感信息的测试产物
- 修改测试用例规则后，同步更新 `references/` 下的说明文件
