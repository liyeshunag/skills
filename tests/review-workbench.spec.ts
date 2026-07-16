/**
 * 综述写作工作台 - 正向主流程自动化测试
 *
 * 流程: 打开网站 → 输入令牌 → 输入主题 → 生成提纲 → 生成全文 →
 *       初稿校对 → 完成校对 → 初稿精修 → 下载全文
 *
 * 特性:
 * - 接口请求/响应监控
 * - 控制台日志采集
 * - 每步截图
 * - 视频录制
 * - 失败自动截图
 */

import { test, expect, Page } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

// ============================================================
// 配置
// ============================================================
const BASE_URL = 'https://review-key.newidea.pro';
const HOME_URL = `${BASE_URL}/home`;
const API_TOKEN = 'sk-glyDul6BZ6zRNWkU15Fc2f4a76D345C4AeEdE0CaE0E63fAf';

// 各阶段超时（提纲和全文生成需要较长时间）
const STEP_TIMEOUT = 5 * 60 * 1000;   // 5 分钟
const LONG_TIMEOUT = 10 * 60 * 1000;  // 10 分钟（全文生成）

// 下载目录
const DOWNLOAD_DIR = path.join(__dirname, '..', 'downloads');

// ============================================================
// 工具函数
// ============================================================

async function setupMonitoring(page: Page) {
  const apiLogs: any[] = [];
  const consoleLogs: any[] = [];

  page.on('request', (req) => {
    const url = req.url();
    if (url.includes('/api/') || url.includes('/v1/') || url.includes('newidea')) {
      apiLogs.push({
        type: 'request',
        method: req.method(),
        url,
        body: req.postData()?.substring(0, 500),
        time: new Date().toISOString(),
      });
    }
  });

  page.on('response', async (res) => {
    const url = res.url();
    if (url.includes('/api/') || url.includes('/v1/') || url.includes('newidea')) {
      let body = '';
      try { body = (await res.text()).substring(0, 1000); } catch { body = '[binary]'; }
      apiLogs.push({
        type: 'response',
        method: res.request().method(),
        url,
        status: res.status(),
        body,
        time: new Date().toISOString(),
      });
    }
  });

  page.on('requestfailed', (req) => {
    apiLogs.push({
      type: 'failed',
      method: req.method(),
      url: req.url(),
      error: req.failure()?.errorText,
      time: new Date().toISOString(),
    });
  });

  page.on('console', (msg) => {
    if (msg.type() === 'error' || msg.type() === 'warning') {
      consoleLogs.push({ type: msg.type(), text: msg.text(), time: new Date().toISOString() });
    }
  });

  page.on('pageerror', (err) => {
    consoleLogs.push({ type: 'pageerror', text: err.message, time: new Date().toISOString() });
  });

  return { apiLogs, consoleLogs };
}

function attachLogs(testInfo: any, apiLogs: any[], consoleLogs: any[], label: string) {
  if (apiLogs.length > 0) {
    testInfo.attach(`${label}-接口日志`, { body: JSON.stringify(apiLogs, null, 2), contentType: 'application/json' });
  }
  if (consoleLogs.length > 0) {
    testInfo.attach(`${label}-控制台日志`, { body: JSON.stringify(consoleLogs, null, 2), contentType: 'application/json' });
  }
}

/** 等待 loading 消失 */
async function waitLoading(page: Page, timeout = LONG_TIMEOUT) {
  try {
    await page.locator('img[alt="Loading"]').waitFor({ state: 'hidden', timeout });
  } catch { /* 已消失 */ }
}

/** 处理弹窗：找到并点击"确定"按钮 */
async function clickDialogConfirm(page: Page) {
  const dialog = page.locator('[role="dialog"]');
  if (await dialog.isVisible({ timeout: 3000 }).catch(() => false)) {
    await dialog.getByText('确定').click();
    await page.waitForTimeout(1000);
  }
}

// ============================================================
// 测试用例：正向主流程
// ============================================================

test.describe('综述写作工作台 - 正向主流程', () => {

  test('完整流程：令牌 → 主题 → 提纲 → 全文 → 校对 → 精修 → 下载', async ({ page }, testInfo) => {
    const { apiLogs, consoleLogs } = await setupMonitoring(page);

    // 确保下载目录存在
    if (!fs.existsSync(DOWNLOAD_DIR)) {
      fs.mkdirSync(DOWNLOAD_DIR, { recursive: true });
    }

    // ============================================================
    // Step 1: 打开网站，输入令牌并保存
    // ============================================================
    await test.step('Step 1: 打开网站并输入令牌', async () => {
      await page.goto(HOME_URL, { waitUntil: 'networkidle' });
      await page.waitForTimeout(2000);

      // 验证页面加载
      await expect(page).toHaveTitle(/综述写作工作台/);
      await expect(page.getByText('综述 AI 写作工作台')).toBeVisible();

      // 验证令牌弹窗
      const dialog = page.locator('[role="dialog"]');
      await expect(dialog).toBeVisible();
      await expect(dialog.getByText(/请输入令牌/)).toBeVisible();

      // 输入令牌
      const tokenInput = dialog.getByRole('textbox', { name: /请输入令牌/ });
      await tokenInput.fill(API_TOKEN);
      await expect(tokenInput).toHaveValue(API_TOKEN);

      // 点击保存（按钮的 accessible name 是 "Close"，用 getByText 匹配）
      await dialog.getByText('保存').click();
      await page.waitForTimeout(1000);

      // 验证弹窗关闭
      await expect(dialog).not.toBeVisible({ timeout: 5000 });

      await testInfo.attach('step1-令牌保存成功', {
        body: await page.screenshot({  }),
        contentType: 'image/png',
      });
    });

    // ============================================================
    // Step 2: 输入综述主题，选择短篇模式，点击生成提纲
    // ============================================================
    await test.step('Step 2: 输入主题并生成提纲', async () => {
      const topicText = '肠道菌群代谢物短链脂肪酸在炎症性肠病中的免疫稳态作用';

      // 输入主题
      const topicInput = page.getByPlaceholder('请输入综述主题概要内容');
      await expect(topicInput).toBeVisible();
      await topicInput.fill(topicText);
      await expect(topicInput).toHaveValue(topicText);

      // 选择短篇模式
      await page.getByText('短篇').first().click();

      // 点击生成提纲
      const generateBtn = page.getByRole('button', { name: /生成提纲/ });
      await expect(generateBtn).toBeEnabled();
      await generateBtn.click();

      // 验证跳转到提纲页
      await page.waitForURL(/\/outline/, { timeout: 30000 });
      expect(page.url()).toContain('/outline');

      await testInfo.attach('step2-已跳转提纲页', {
        body: await page.screenshot({  }),
        contentType: 'image/png',
      });
    });

    // ============================================================
    // Step 3: 等待提纲生成完成，点击生成全文
    // ============================================================
    await test.step('Step 3: 等待提纲生成 → 生成全文', async () => {
      // 等待提纲生成完成
      await waitLoading(page, STEP_TIMEOUT);

      // 验证下载提纲和生成全文按钮可用
      const downloadOutlineBtn = page.getByRole('button', { name: /下载提纲/ });
      const generateFullBtn = page.getByRole('button', { name: /生成全文/ });
      await expect(downloadOutlineBtn).toBeEnabled({ timeout: STEP_TIMEOUT });
      await expect(generateFullBtn).toBeEnabled({ timeout: 10000 });

      // 验证提纲内容存在
      const treeItems = page.locator('[role="treeitem"]');
      const itemCount = await treeItems.count();
      expect(itemCount).toBeGreaterThan(5);

      await testInfo.attach('step3-提纲生成完成', {
        body: await page.screenshot({  }),
        contentType: 'image/png',
      });

      // 点击生成全文
      await generateFullBtn.click();
      await page.waitForTimeout(2000);

      // 处理确认弹窗（语言/参考文献选择）
      await clickDialogConfirm(page);

      await testInfo.attach('step3-已确认生成全文', {
        body: await page.screenshot({  }),
        contentType: 'image/png',
      });
    });

    // ============================================================
    // Step 4: 等待全文生成 → 初稿校对 → 完成校对
    // ============================================================
    await test.step('Step 4: 初稿校对 → 完成校对', async () => {
      // 等待跳转到校对页
      await page.waitForURL(/\/proofread/, { timeout: 30000 });
      expect(page.url()).toContain('/proofread');

      // 验证 STEP 3 高亮
      await expect(page.getByText('初稿校对')).toBeVisible();

      // 等待文章内容生成完成
      await waitLoading(page, LONG_TIMEOUT);

      // 等待"完成校对"按钮可用
      const finishProofreadBtn = page.getByRole('button', { name: /完成校对/ });
      await expect(finishProofreadBtn).toBeEnabled({ timeout: LONG_TIMEOUT });

      // 验证文章内容存在
      const articleContent = page.locator('[role="treeitem"]');
      const contentCount = await articleContent.count();
      expect(contentCount).toBeGreaterThan(10);

      await testInfo.attach('step4-文章生成完成', {
        body: await page.screenshot({  }),
        contentType: 'image/png',
      });

      // 点击完成校对
      await finishProofreadBtn.click();
      await page.waitForTimeout(2000);

      // 处理确认弹窗
      await clickDialogConfirm(page);

      await testInfo.attach('step4-已确认完成校对', {
        body: await page.screenshot({  }),
        contentType: 'image/png',
      });
    });

    // ============================================================
    // Step 5: 初稿精修 → 本地保存（下载全文）
    // ============================================================
    await test.step('Step 5: 初稿精修 → 下载全文', async () => {
      // 等待跳转到精修页
      await page.waitForURL(/\/edit/, { timeout: 30000 });
      expect(page.url()).toContain('/edit');

      // 验证 STEP 4 高亮
      await expect(page.getByText('初稿精修')).toBeVisible();

      // 验证精修功能按钮
      await expect(page.getByRole('button', { name: /润色/ })).toBeVisible();
      await expect(page.getByRole('button', { name: /降重/ })).toBeVisible();
      await expect(page.getByRole('button', { name: /翻译/ })).toBeVisible();

      await testInfo.attach('step5-精修页面', {
        body: await page.screenshot({}),
        contentType: 'image/png',
      });

      // 点击本地保存 → 等待下载完成
      const saveBtn = page.getByRole('button', { name: /本地保存/ });
      await expect(saveBtn).toBeVisible();

      // 使用 Promise 监听下载事件
      const downloadPromise = page.waitForEvent('download', { timeout: 30000 });
      await saveBtn.click();
      await page.waitForTimeout(1000);

      // 处理保存弹窗
      await clickDialogConfirm(page);

      // 等待下载完成
      const download = await downloadPromise;
      const downloadPath = path.join(DOWNLOAD_DIR, download.suggestedFilename());
      await download.saveAs(downloadPath);

      console.log(`文件已下载: ${downloadPath}`);
      expect(fs.existsSync(downloadPath)).toBe(true);

      await testInfo.attach('step5-下载完成', {
        body: await page.screenshot({}),
        contentType: 'image/png',
      });
    });

    // ============================================================
    // 附加完整日志到报告
    // ============================================================
    attachLogs(testInfo, apiLogs, consoleLogs, '完整流程');
  });

});
