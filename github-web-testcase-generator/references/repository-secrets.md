# Repository Secrets 规则

敏感值必须来自 GitHub Repository secrets 或运行时环境变量。不要把项目密钥明文写进测试用例或提交文件。

## 允许引用的 Secret 名称

只能引用 secret 名称：

- `TEST_BASE_URL`
- `TEST_USERNAME`
- `TEST_PASSWORD`
- `TEST_USER_EMAIL`
- `TEST_USER_PASSWORD`
- `TEST_LIMITED_EMAIL`
- `TEST_LIMITED_PASSWORD`
- `TEST_OTP_SECRET`
- `TEST_API_TOKEN`
- 仓库中已经使用的项目自定义 secret 名称

不要包含真实 URL、用户名、密码、cookie、token、API key 或 OTP seed。

## 必须提醒用户

当生成的用例依赖环境数据时，提醒用户：

请在 GitHub 仓库设置中手工配置所需值：`Settings -> Secrets and variables -> Actions`。

## 自动化执行用法

在 GitHub Actions 中通过表达式注入：

```yaml
env:
  TEST_BASE_URL: ${{ secrets.TEST_BASE_URL }}
  TEST_USERNAME: ${{ secrets.TEST_USERNAME }}
  TEST_PASSWORD: ${{ secrets.TEST_PASSWORD }}
```

在自然语言测试步骤中只引用环境变量名：

- 打开测试网址，测试网址从 `TEST_BASE_URL` 获取
- 输入测试账号，测试账号从 `TEST_USERNAME` 获取
- 输入测试密码，测试密码从 `TEST_PASSWORD` 获取

如果仓库使用 `TEST_USER_EMAIL` 和 `TEST_USER_PASSWORD`，优先沿用仓库已有命名。

## 硬性规则

- 不要打印 secret 值。
- 不要提交包含真实值的 `.env` 文件。
- 不要在 YAML 测试用例中写入 secret 值。
- 不要创建看起来像真实账号密码的假凭证。
- 除非用户明确确认安全的生产测试策略，否则不要使用生产凭证生成或执行测试。
