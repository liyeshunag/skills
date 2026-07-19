# github-generator-testcase

## Skill 介绍

`github-generator-testcase` 是一个企业级、可长期维护的 Agent Skill，用于自动扫描 GitHub 仓库源码、Pull Request (PR)、Commit Diff，分析新增/修改功能，并生成高质量的中文测试用例。

### 核心特性

- **增量生成**：基于 `testcase-history.json` 实现增量更新，仅生成新增功能的测试用例，避免重复
- **智能去重**：自动对比历史 CSV，检测重复用例并跳过
- **标准化输出**：统一的 UTF-8 CSV 格式，字段固定，编号连续
- **多场景覆盖**：每个功能点覆盖 25 类测试场景（正向/反向/边界/安全/性能等）
- **PR/Commit 感知**：自动分析 PR Diff 和 Commit Diff，识别新增/修改/删除的代码
- **GitHub 集成**：支持扫描整个仓库、指定分支、指定 Commit、指定 PR

## 能力说明

### ① 扫描能力

| 扫描目标 | 说明 |
|---------|------|
| 整个 Repository | 扫描仓库所有源码 |
| 指定 Branch | 扫描特定分支 |
| 指定 Commit | 扫描某个 Commit 的变更 |
| 指定 PR | 扫描 Pull Request 的 Diff |
| 指定 Diff | 扫描自定义 Diff 内容 |

### ② 自动识别

- 新增页面 / 路由
- 新增模块 / 组件
- 新增接口 / API
- 新增按钮 / 菜单
- 新增权限 / 角色
- 新增配置项
- 新增数据库字段 / 表
- 新增业务流程
- 新增 AI/ML 流程

### ③ 自动理解

- 业务逻辑与流程
- 页面交互与跳转
- 接口调用链与数据流
- 权限控制逻辑
- 异常处理与边界处理

### ④ 自动分析

- 新增功能点
- 修改功能的影响范围
- 删除功能的回归范围
- 潜在风险点

## 目录结构说明

```
github-generator-testcase/
├── skill.md                          # 本文件：Skill 定义与说明
├── README.md                         # 用户使用文档
├── reference/
│   ├── testcase-standard.md          # 测试用例编写规范
│   ├── testcase-template.csv         # CSV 模板文件
│   ├── testcase-history.json         # 编号历史与生成记录
│   ├── prompt.md                     # LLM Prompt 模板库
│   └── naming-rule.md               # 编号与命名规则
├── scripts/
│   ├── scan_repository.py            # 仓库扫描主入口
│   ├── parse_diff.py                 # Git Diff 解析器
│   ├── generate_testcase.py          # LLM 调用生成测试用例
│   ├── merge_csv.py                  # CSV 合并工具
│   ├── testcase_id_manager.py        # 编号管理器
│   ├── duplicate_checker.py          # 重复检测器
│   └── export_csv.py                 # CSV 导出工具
├── assets/
│   ├── csv-example.png               # CSV 示例截图
│   ├── workflow.png                  # 工作流程图
│   └── architecture.png              # 架构图
```

## 输入参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `repo_url` | string | 是 | GitHub 仓库 URL |
| `branch` | string | 否 | 目标分支，默认 main |
| `commit_sha` | string | 否 | 目标 Commit SHA |
| `pr_number` | int | 否 | PR 编号 |
| `diff_content` | string | 否 | 自定义 Diff 内容 |
| `output_dir` | string | 否 | 输出目录，默认当前目录 |
| `project_name` | string | 否 | 项目名称，用于 CSV 命名 |
| `incremental` | bool | 否 | 是否增量模式，默认 true |
| `coverage_level` | string | 否 | 覆盖级别：basic/standard/full，默认 standard |

## 输出格式

### CSV 文件

文件名：`<ProjectName>_TestCases.csv`

编码：UTF-8 with BOM

字段顺序（不可修改）：

```
测试用例序号,模块,测试点,测试用例标题,优先级,操作步骤,预期结果,最终结果,备注,测试人
```

### 示例输出

```
测试用例序号,模块,测试点,测试用例标题,优先级,操作步骤,预期结果,最终结果,备注,测试人
testcase_001,登录,正向功能,登录成功,P0,1 打开登录页\n2 输入有效用户名和密码\n3 点击登录,页面跳转至首页\n接口返回200\nToken写入LocalStorage,,,
testcase_002,登录,反向功能,登录密码错误,P1,1 打开登录页\n2 输入有效用户名\n3 输入错误密码\n4 点击登录,提示"密码错误"\n停留在登录页\n接口返回401,,,
```

## 工作流程

```
┌─────────────────────────────────────────────────────────────┐
│                      整体工作流程                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. 扫描 Repository                                         │
│       ↓                                                     │
│  2. 读取历史 CSV (testcase-history.json)                     │
│       ↓                                                     │
│  3. 读取 History (编号记录)                                  │
│       ↓                                                     │
│  4. 扫描 PR / Commit / Diff                                 │
│       ↓                                                     │
│  5. 解析 Diff → 识别变更文件                                  │
│       ↓                                                     │
│  6. 识别新增功能（页面/模块/接口/组件/流程）                    │
│       ↓                                                     │
│  7. LLM 理解业务逻辑                                         │
│       ↓                                                     │
│  8. 生成测试点（覆盖 25 类场景）                               │
│       ↓                                                     │
│  9. 生成结构化测试用例                                        │
│       ↓                                                     │
│ 10. 去重检测（对比历史用例）                                   │
│       ↓                                                     │
│ 11. 编号递增（继续上次编号）                                   │
│       ↓                                                     │
│ 12. 导出标准 CSV                                             │
│       ↓                                                     │
│ 13. 更新 History                                             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Prompt 模板

### 系统 Prompt（用于 LLM 理解代码）

```
你是一名资深测试工程师，具备以下能力：
1. 阅读并理解前端/后端代码
2. 分析业务逻辑和用户流程
3. 识别功能点和测试场景
4. 生成高质量中文测试用例

请严格按照以下规范生成测试用例：
- 测试用例编号连续递增
- 标题简洁明确，符合业务语义
- 操作步骤短小清晰可执行
- 预期结果具体明确
- 覆盖正向/反向/边界/安全/性能等场景
```

### 功能分析 Prompt

```
请分析以下代码变更，识别：
1. 新增了哪些功能？
2. 修改了哪些功能？
3. 删除了哪些功能？
4. 影响了哪些模块？
5. 潜在风险有哪些？

代码变更（Diff）：
{diff_content}
```

### 测试用例生成 Prompt

```
基于以下新增功能，请生成中文测试用例：

功能描述：{feature_description}

要求：
- 至少覆盖 25 类测试场景
- 遵循 CSV 标准格式
- 测试标题简洁业务化
- 预期结果具体明确
```

## 执行流程示例

### 首次扫描仓库

```bash
python scripts/scan_repository.py \
  --repo https://github.com/example/helix.git \
  --branch main \
  --project-name Helix
```

### 增量扫描 PR

```bash
python scripts/scan_repository.py \
  --repo https://github.com/example/helix.git \
  --pr 42 \
  --incremental
```

### 扫描指定 Commit

```bash
python scripts/scan_repository.py \
  --repo https://github.com/example/helix.git \
  --commit abc123def456
```

## 限制

1. **GitHub 访问**：需要配置有效的 GitHub Token（环境变量 `GITHUB_TOKEN`）
2. **LLM 依赖**：测试用例生成依赖 LLM API，需要配置 API Key
3. **仓库大小**：超大型仓库（>10GB）建议按模块分批扫描
4. **语言支持**：当前主要支持中文测试用例输出
5. **增量模式**：增量模式依赖 `testcase-history.json`，需保证该文件完整性

## 最佳实践

1. **首次使用**：先对稳定版本执行一次完整扫描，建立基线
2. **日常使用**：每次 PR 合并前执行增量扫描
3. **版本管理**：将 `reference/testcase-history.json` 和 CSV 文件纳入 Git 管理
4. **定期审计**：每季度人工审查生成的测试用例质量
5. **Prompt 优化**：根据实际效果持续优化 `reference/prompt.md`

## 异常处理

| 异常场景 | 处理方式 |
|---------|---------|
| GitHub API 限流 | 自动重试 + 指数退避 |
| LLM API 超时 | 重试 3 次，失败记录日志 |
| 仓库克隆失败 | 提示用户检查网络和权限 |
| Diff 解析失败 | 记录错误日志，跳过该文件 |
| CSV 写入冲突 | 锁定文件，排队写入 |
| 编号冲突 | 自动检测并使用锁机制 |

## 版本管理

- 主版本号：Skill 结构重大变更
- 次版本号：新增脚本或功能
- 修订号：Bug 修复或 Prompt 优化

版本记录在 `skill.md` 文件头部的元数据中。

## 增量更新机制

### 核心原理

```
┌──────────────┐     ┌──────────────────┐     ┌──────────────┐
│ 扫描新代码    │ ──→ │ 对比 testcase-    │ ──→ │ 仅生成新增    │
│ (PR/Diff)    │     │ history.json     │     │ 测试用例      │
└──────────────┘     └──────────────────┘     └──────────────┘
```

### 去重策略

1. **模块级去重**：已扫描过的模块不重复分析
2. **功能点去重**：已生成测试用例的功能点跳过
3. **标题模糊匹配**：相似度 > 80% 的标题视为重复
4. **Diff 哈希去重**：相同 Diff 内容不重复处理

### History 结构

```json
{
  "version": "1.0.0",
  "current_index": 235,
  "project_name": "Helix",
  "last_scan": "2026-07-19T10:30:00Z",
  "generated_modules": [
    {
      "module": "用户登录",
      "testcase_count": 15,
      "testcase_ids": ["testcase_001", "testcase_015"],
      "source_commit": "abc123",
      "generated_at": "2026-07-18T08:00:00Z"
    }
  ],
  "scanned_commits": ["abc123", "def456"],
  "scanned_prs": [1, 2, 3]
}
```
