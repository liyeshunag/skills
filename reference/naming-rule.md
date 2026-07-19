# 编号与命名规则

## 一、测试用例编号规则

### 1.1 编号格式

```
testcase_{NNN}
```

- `testcase_`：固定前缀
- `{NNN}`：3 位数字，不足补零（001, 002, ..., 999）

### 1.2 编号生命周期

```
首次生成: testcase_001 → testcase_N
增量生成: testcase_{N+1} → testcase_{N+M}
```

### 1.3 编号管理

编号由 `testcase_id_manager.py` 统一管理：

```python
class TestCaseIDManager:
    """管理测试用例编号的分配与持久化"""
    
    def __init__(self, history_path: str):
        self.history = self._load_history(history_path)
        self.current_index = self.history["current_index"]
    
    def allocate(self, count: int) -> List[str]:
        """分配 count 个新编号，返回编号列表"""
        ids = []
        for i in range(count):
            self.current_index += 1
            ids.append(f"testcase_{self.current_index:03d}")
        self._save_history()
        return ids
    
    def get_next_index(self) -> int:
        """获取下一个可用编号（不分配）"""
        return self.current_index + 1
```

### 1.4 编号约束

- ❌ 不允许跳号
- ❌ 不允许重用已废弃编号
- ❌ 不允许手动修改编号
- ✅ 删除用例后编号不回收
- ✅ 编号全局唯一（同项目内）

## 二、CSV 文件命名规则

### 2.1 项目测试用例文件

```
{ProjectName}_TestCases.csv
```

示例：
| 项目 | 文件名 |
|------|--------|
| Helix | `Helix_TestCases.csv` |
| MedAI | `MedAI_TestCases.csv` |
| DataPlatform | `DataPlatform_TestCases.csv` |

### 2.2 项目名提取规则

1. 从 GitHub 仓库名提取（如 `helix-web` → `Helix`）
2. 从用户参数 `--project-name` 指定
3. 从 `testcase-history.json` 读取

### 2.3 项目名格式要求

- PascalCase（首字母大写）
- 仅包含字母和数字
- 2-30 个字符

## 三、模块命名规则

### 3.1 模块名

```
{功能模块名}
```

- 2-6 个中文字符
- 按功能划分，不按技术分层
- 示例：登录、注册、用户管理、订单管理、AI 生成

### 3.2 模块名提取规则

1. 从文件路径推断（如 `src/pages/login/` → `登录`）
2. 从组件名推断（如 `UserProfile.tsx` → `用户资料`）
3. 从路由名推断（如 `/dashboard/settings` → `设置`）
4. LLM 辅助理解业务语义

## 四、测试点命名规则

### 4.1 标准测试点名称

使用以下标准名称（来自 25 类场景）：

```
正向功能
反向功能
空值测试
Null值测试
边界值测试
最大长度测试
最小长度测试
特殊字符测试
SQL注入测试
XSS测试
权限测试
重复提交测试
并发测试
网络异常测试
超时测试
浏览器兼容测试
分辨率测试
国际化测试
文件格式测试
文件大小测试
AI异常返回测试
服务重启测试
Token失效测试
Session过期测试
回归测试
```

### 4.2 自定义测试点

如果以上标准名称不适用，可使用业务具体场景名：

```
登录流程
数据导出
权限校验
流程审批
```

## 五、标题命名规则

### 5.1 格式

```
{操作对象}{操作}{结果}
```

### 5.2 示例

| 操作对象 | 操作 | 结果 | 完整标题 |
|---------|------|------|---------|
| 登录 | - | 成功 | 登录成功 |
| 密码 | 输入错误 | 提示错误 | 登录密码错误 |
| PDF文件 | 上传 | 成功 | 上传PDF成功 |
| 文章 | 删除 | 失败提示 | 删除文章失败提示 |
| AI生成 | - | 超时 | AI生成论文超时 |
| 用户名 | 输入特殊字符 | 注册失败 | 特殊字符用户名注册失败 |

### 5.3 标题动词库

| 分类 | 常用动词 |
|------|---------|
| 创建 | 新建、添加、创建、上传、导入 |
| 读取 | 查看、搜索、查询、筛选、导出 |
| 更新 | 编辑、修改、更新、保存、提交 |
| 删除 | 删除、移除、清空、注销 |
| 状态 | 启用、禁用、锁定、激活、审批 |
| 异常 | 失败、超时、错误、异常、拒绝 |
| 展示 | 显示、隐藏、跳转、刷新、加载 |

## 六、History 文件命名规则

### 6.1 文件路径

```
reference/testcase-history.json
```

固定路径，不可修改。

### 6.2 版本号规则

History 文件通过 `version` 字段标识格式版本：

- `1.0.0`：初始版本
- `1.1.0`：增加 `file_hashes` 字段
- `1.2.0`：增加 `scanned_branches` 字段

### 6.3 兼容性

Skill 升级后，自动检测 History 版本并迁移数据结构。

## 七、Diff 解析中的命名映射

### 7.1 代码 → 模块映射

| 代码特征 | 模块推断 |
|---------|---------|
| `src/pages/login/` | 登录 |
| `src/pages/register/` | 注册 |
| `src/components/Upload/` | 文件上传 |
| `api/user.py` | 用户管理 |
| `POST /api/order` | 订单管理 |
| `table: user_roles` | 权限管理 |

### 7.2 代码 → 功能点映射

| 代码特征 | 功能点推断 |
|---------|-----------|
| 新增路由 `Route path="/new-page"` | 新增页面 |
| 新增 `POST /api/xxx` | 新增接口 |
| 新增 `const [modalVisible]` | 新增弹窗 |
| 新增 `<Button onClick={...}>` | 新增按钮 |
| 新增 `ALTER TABLE ADD COLUMN` | 新增数据库字段 |
| 新增 `if (role === 'admin')` | 新增权限逻辑 |
