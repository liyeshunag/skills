# github-generator-testcase

> 企业级 GitHub 仓库测试用例自动生成 Skill

通过扫描 GitHub 仓库源码、Pull Request、Commit Diff，自动分析新增功能，生成高质量中文测试用例。

## 目录

- [快速开始](#快速开始)
- [安装配置](#安装配置)
- [使用指南](#使用指南)
- [示例命令](#示例命令)
- [工作原理](#工作原理)
- [FAQ](#faq)
- [维护升级](#维护升级)

---

## 快速开始

```bash
# 1. 设置环境变量
export GITHUB_TOKEN="ghp_xxxxxxxxxxxx"
export OPENAI_API_KEY="sk-xxxxxxxxxxxx"

# 2. 首次全量扫描
python scripts/scan_repository.py \
  --repo https://github.com/your-org/your-repo.git \
  --project-name YourProject

# 3. 查看生成的测试用例
cat YourProject_TestCases.csv
```

## 安装配置

### 环境要求

- Python 3.9+
- Git 2.30+
- GitHub Token（用于访问仓库）
- OpenAI API Key（用于 LLM 生成测试用例）

### 安装依赖

```bash
pip install openai
```

### 环境变量配置

```bash
# 必需
export GITHUB_TOKEN="your_github_personal_access_token"
export OPENAI_API_KEY="your_openai_api_key"

# 可选
export OPENAI_API_BASE="https://api.openai.com/v1"  # 自定义 API 地址
export LLM_MODEL="gpt-4"                              # LLM 模型选择
```

### GitHub Token 权限要求

- `repo` - 访问私有仓库（如使用公开仓库则不需要）
- `read:org` - 读取组织信息（可选）

## 使用指南

### 1. 扫描整个仓库

首次使用时，对仓库进行全量扫描：

```bash
python scripts/scan_repository.py \
  --repo https://github.com/example/helix.git \
  --branch main \
  --project-name Helix \
  --output-dir ./output
```

### 2. 扫描 Pull Request

每次有新 PR 时，增量扫描 PR 变更：

```bash
python scripts/scan_repository.py \
  --repo https://github.com/example/helix.git \
  --pr 42 \
  --incremental \
  --project-name Helix
```

### 3. 扫描指定 Commit

针对某个特定的 Commit 进行扫描：

```bash
python scripts/scan_repository.py \
  --repo https://github.com/example/helix.git \
  --commit abc123def456 \
  --project-name Helix
```

### 4. 扫描自定义 Diff

如果你已有 Diff 文件，可以直接扫描：

```bash
git diff main...feature-branch > changes.diff

python scripts/scan_repository.py \
  --diff ./changes.diff \
  --project-name Helix
```

### 5. 全量重新生成

禁用增量模式，重新生成所有测试用例：

```bash
python scripts/scan_repository.py \
  --repo https://github.com/example/helix.git \
  --project-name Helix \
  --full
```

### 6. 控制覆盖级别

```bash
# 基础覆盖（10 类场景）
python scripts/scan_repository.py ... --coverage-level basic

# 标准覆盖（18 类场景，默认）
python scripts/scan_repository.py ... --coverage-level standard

# 完整覆盖（25 类场景）
python scripts/scan_repository.py ... --coverage-level full
```

### 7. 避免重复生成

增量模式默认开启，Skill 会自动：

1. 读取 `reference/testcase-history.json` 中的扫描记录
2. 对比已生成的模块和功能点
3. 跳过已存在的测试用例
4. 仅生成新增功能的测试用例

手动检查重复：

```bash
python scripts/duplicate_checker.py
```

### 8. 维护 Reference

Reference 目录包含 Skill 的配置和知识库：

| 文件 | 说明 | 维护方式 |
|------|------|---------|
| `testcase-standard.md` | 测试用例规范 | 按项目需要调整标准 |
| `testcase-template.csv` | CSV 模板 | 不要修改字段顺序 |
| `testcase-history.json` | 生成历史 | 由 Skill 自动维护 |
| `prompt.md` | Prompt 模板 | 可按需优化 Prompt |
| `naming-rule.md` | 命名规则 | 可扩展模块映射表 |

### 9. 升级 Skill

```bash
# 1. 备份当前 reference
cp -r reference reference_backup_$(date +%Y%m%d)

# 2. 拉取最新 Skill
git pull origin main

# 3. 迁移 history
python scripts/migrate_history.py

# 4. 验证
python scripts/scan_repository.py --repo ... --project-name ... --incremental
```

## 示例命令

### 场景一：新项目接入

```bash
# Step 1: 设置项目
export PROJECT_NAME="MedAI"
export REPO_URL="https://github.com/example/medai.git"

# Step 2: 全量扫描
python scripts/scan_repository.py \
  --repo $REPO_URL \
  --project-name $PROJECT_NAME \
  --coverage-level full \
  --output-dir ./output/$PROJECT_NAME

# Step 3: 查看结果
wc -l ./output/$PROJECT_NAME/MedAI_TestCases.csv
```

### 场景二：CI/CD 集成

```yaml
# .github/workflows/generate-testcases.yml
name: Generate Test Cases

on:
  pull_request:
    types: [opened, synchronize]

jobs:
  generate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - name: Install dependencies
        run: pip install openai
      - name: Generate test cases
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: |
          python scripts/scan_repository.py \
            --repo ${{ github.repositoryUrl }} \
            --pr ${{ github.event.pull_request.number }} \
            --project-name MyProject \
            --incremental
      - name: Upload CSV
        uses: actions/upload-artifact@v3
        with:
          name: test-cases
          path: MyProject_TestCases.csv
```

### 场景三：批量 PR 扫描

```bash
#!/bin/bash
# scan_prs.sh - 批量扫描多个 PR

PR_LIST=(42 43 44 45 46)
REPO="https://github.com/example/helix.git"
PROJECT="Helix"

for pr in "${PR_LIST[@]}"; do
  echo "Scanning PR #$pr..."
  python scripts/scan_repository.py \
    --repo $REPO \
    --pr $pr \
    --project-name $PROJECT \
    --incremental
done

echo "All PRs scanned!"
```

## 工作原理

### 整体架构

```
GitHub Repository / PR / Commit
              │
              ▼
     ┌────────────────┐
     │ scan_repository │  ← 主入口
     └───────┬────────┘
             │
     ┌───────▼────────┐
     │  parse_diff    │  ← Git Diff 解析
     └───────┬────────┘
             │
     ┌───────▼────────┐
     │ 识别新增功能    │  ← 业务分析
     └───────┬────────┘
             │
     ┌───────▼────────┐
     │ generate_       │  ← LLM 生成
     │ testcase        │
     └───────┬────────┘
             │
     ┌───────▼────────┐
     │ duplicate_      │  ← 去重检测
     │ checker         │
     └───────┬────────┘
             │
     ┌───────▼────────┐
     │ merge_csv +     │  ← 合并与导出
     │ export_csv      │
     └───────┬────────┘
             │
     ┌───────▼────────┐
     │ testcase-id-    │  ← 编号管理
     │ manager         │
     └────────────────┘
```

### 增量更新机制

```
新 PR/Commit
    │
    ▼
扫描 Diff ──→ 提取变更文件
    │
    ▼
读取 testcase-history.json
    │
    ▼
对比已扫描的 commit/PR/module
    │
    ├── 已存在 → 跳过
    │
    └── 新增 → 生成测试用例 → 追加 CSV → 更新 History
```

### 去重策略

| 级别 | 检测方式 | 阈值 |
|------|---------|------|
| L1 | 标题完全相同 | 100% |
| L2 | 标题模糊匹配 | > 80% |
| L3 | 同模块+同测试点+步骤相似 | > 85% |
| L4 | 综合相似度 | > 75% |

## CSV 输出说明

### 文件名格式

```
{ProjectName}_TestCases.csv
```

### 字段说明

| 字段 | 说明 | 示例 |
|------|------|------|
| 测试用例序号 | 唯一编号 testcase_NNN | testcase_001 |
| 模块 | 功能模块 | 登录 |
| 测试点 | 测试场景 | 正向功能 |
| 测试用例标题 | 简洁业务标题 | 登录成功 |
| 优先级 | P0/P1/P2/P3 | P0 |
| 操作步骤 | 编号分步 | 1 输入用户名\n2 输入密码 |
| 预期结果 | 具体预期 | 跳转到首页\n显示欢迎信息 |
| 最终结果 | 执行后填写 | |
| 备注 | 附加说明 | |
| 测试人 | 执行人 | |

### 在 Excel 中打开

直接双击 CSV 文件即可在 Excel/WPS 中打开。如果中文乱码，请确认文件编码为 **UTF-8 with BOM**。

## FAQ

### Q: 需要什么权限？

**A:** 需要 GitHub Personal Access Token（公开仓库可不设置）和 OpenAI API Key。

### Q: 如何避免重复生成？

**A:** 默认开启增量模式（`--incremental`），Skill 会自动读取 `testcase-history.json` 跳过已扫描的 commit/PR/模块。

### Q: 生成的测试用例质量如何？

**A:** 依赖 LLM 模型质量。推荐使用 GPT-4 获得最佳效果。也可以手动优化 `reference/prompt.md` 来提升质量。

### Q: 支持哪些编程语言？

**A:** 语言无关。Skill 通过代码模式识别功能点，不依赖特定编程语言。

### Q: 如何修改生成规范？

**A:** 编辑 `reference/testcase-standard.md` 和 `reference/prompt.md`。

### Q: 编号可以重置吗？

**A:** 可以。运行 `python scripts/testcase_id_manager.py` 查看当前状态。使用 `--reset` 参数重置编号（谨慎使用）。

### Q: 生成的 CSV 可以直接导入 TAPD/Jira 吗？

**A:** 可以。CSV 格式兼容主流测试管理工具的导入格式。可能需要根据具体工具的字段映射做调整。

### Q: 如何处理超大型仓库？

**A:** 建议：
1. 按模块分批扫描（指定文件路径）
2. 使用 `--coverage-level basic` 减少生成量
3. 优先扫描变更频繁的模块

### Q: 没有 LLM API Key 可以使用吗？

**A:** 可以。Skill 内置了基于规则的测试用例生成器作为回退方案。虽然覆盖度和质量不如 LLM，但可以提供基本的测试框架。

## 维护升级

### 版本策略

```
v{major}.{minor}.{patch}

major: Skill 结构重大变更
minor: 新增脚本或功能
patch: Bug修复或Prompt优化
```

### 升级步骤

1. 备份 `reference/` 目录
2. 更新 Skill 文件
3. 运行迁移脚本（如有）
4. 验证历史数据兼容性
5. 执行测试扫描验证

### 贡献指南

1. Fork 本仓库
2. 修改 `reference/prompt.md` 优化 Prompt
3. 修改 `scripts/` 优化脚本逻辑
4. 提交 PR

## 目录结构

```
github-generator-testcase/
├── skill.md                    # Skill 定义文件
├── README.md                   # 本文件
├── reference/
│   ├── testcase-standard.md    # 测试用例规范
│   ├── testcase-template.csv   # CSV 模板
│   ├── testcase-history.json   # 历史记录
│   ├── prompt.md               # Prompt 模板
│   └── naming-rule.md          # 命名规则
├── scripts/
│   ├── scan_repository.py      # 主扫描入口
│   ├── parse_diff.py           # Diff 解析器
│   ├── generate_testcase.py    # 测试用例生成
│   ├── duplicate_checker.py    # 重复检测
│   ├── merge_csv.py            # CSV 合并
│   ├── testcase_id_manager.py  # 编号管理
│   └── export_csv.py           # CSV 导出
└── assets/
    └── README.md               # 资源文件说明
```

## License

MIT
