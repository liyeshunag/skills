/**
 * 自定义测试报告生成器
 * 解析 Playwright JSON 报告 → 生成精美的 Markdown 测试报告
 *
 * 用法: node scripts/generate-report.js
 */

const fs = require('fs');
const path = require('path');

// ============================================================
// 配置
// ============================================================
const REPORT_CONFIG = {
  jsonReportPath: path.join(__dirname, '..', 'test-results.json'),
  outputPath: path.join(__dirname, '..', 'TEST_REPORT.md'),
  projectName: '综述写作工作台',
  baseURL: 'https://review-key.newidea.pro/home',
};

// ============================================================
// 工具函数
// ============================================================

/** 获取当前时间格式化字符串 */
function formatDateTime() {
  const now = new Date();
  return now.toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' });
}

/** 获取当前日期 */
function formatDate() {
  const now = new Date();
  return now.toLocaleDateString('zh-CN', { timeZone: 'Asia/Shanghai' });
}

/** 获取状态 Emoji */
function getStatusEmoji(status) {
  switch (status) {
    case 'passed': return '✅';
    case 'failed': return '❌';
    case 'timedOut': return '⏰';
    case 'skipped': return '⏭️';
    case 'interrupted': return '⚠️';
    default: return '❓';
  }
}

/** 获取状态中文 */
function getStatusText(status) {
  switch (status) {
    case 'passed': return '通过';
    case 'failed': return '失败';
    case 'timedOut': return '超时';
    case 'skipped': return '跳过';
    case 'interrupted': return '中断';
    default: return status;
  }
}

/** 计算通过率颜色 */
function getPassRateColor(rate) {
  if (rate >= 90) return 'brightgreen';
  if (rate >= 70) return 'yellow';
  if (rate >= 50) return 'orange';
  return 'red';
}

/** 截断错误信息 */
function truncateError(error, maxLen = 300) {
  if (!error) return '';
  if (error.length <= maxLen) return error;
  return error.substring(0, maxLen) + '...';
}

/** 格式化耗时 */
function formatDuration(ms) {
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  const minutes = Math.floor(ms / 60000);
  const seconds = Math.floor((ms % 60000) / 1000);
  return `${minutes}m ${seconds}s`;
}

// ============================================================
// 数据解析
// ============================================================

function parseReport() {
  if (!fs.existsSync(REPORT_CONFIG.jsonReportPath)) {
    return null;
  }

  try {
    const raw = fs.readFileSync(REPORT_CONFIG.jsonReportPath, 'utf-8');
    return JSON.parse(raw);
  } catch (err) {
    console.error('解析 JSON 报告失败:', err.message);
    return null;
  }
}

// ============================================================
// 报告生成
// ============================================================

function generateReport(reportData) {
  const lines = [];

  // ========== 标题区 ==========
  lines.push(`# 🧪 ${REPORT_CONFIG.projectName} - 自动化测试报告`);
  lines.push('');
  lines.push(`> 📅 报告生成时间：**${formatDateTime()}**`);
  lines.push(`> 🌐 测试地址：[${REPORT_CONFIG.baseURL}](${REPORT_CONFIG.baseURL})`);
  lines.push('');

  if (!reportData) {
    lines.push('## ⚠️ 无测试数据');
    lines.push('');
    lines.push('未找到测试报告 JSON 文件，请检查测试是否正确执行。');
    return lines.join('\n');
  }

  // ========== 总体统计 ==========
  const suites = reportData.suites || [];
  const allTests = [];

  function collectTests(suite) {
    if (suite.specs) {
      for (const spec of suite.specs) {
        if (spec.tests) {
          for (const test of spec.tests) {
            allTests.push({
              ...test,
              title: spec.title || test.title || 'Unknown Test',
              suiteTitle: suite.title,
              file: spec.file,
            });
          }
        }
      }
    }
    if (suite.suites) {
      for (const child of suite.suites) {
        collectTests(child);
      }
    }
  }

  for (const suite of suites) {
    collectTests(suite);
  }

  const total = allTests.length;
  const passed = allTests.filter(t => t.status === 'expected').length;
  const failed = allTests.filter(t => t.status === 'unexpected').length;
  const skipped = allTests.filter(t => t.status === 'skipped').length;
  const timedOut = allTests.filter(t => t.status === 'timedOut').length;
  const passRate = total > 0 ? Math.round((passed / total) * 100) : 0;

  // ========== 概览卡片 ==========
  lines.push('## 📊 测试概览');
  lines.push('');
  lines.push('| 指标 | 数值 |');
  lines.push('|------|------|');
  lines.push(`| 📋 测试总数 | **${total}** |`);
  lines.push(`| ✅ 通过 | **${passed}** |`);
  lines.push(`| ❌ 失败 | **${failed}** |`);
  lines.push(`| ⏭️ 跳过 | **${skipped}** |`);
  lines.push(`| ⏰ 超时 | **${timedOut}** |`);
  lines.push(`| 📈 通过率 | **${passRate}%** |`);
  lines.push('');

  // ========== 通过率进度条 ==========
  const barLen = 20;
  const filledLen = Math.round((passRate / 100) * barLen);
  const emptyLen = barLen - filledLen;
  const bar = '█'.repeat(filledLen) + '░'.repeat(emptyLen);
  lines.push('### 通过率');
  lines.push('');
  lines.push('```');
  lines.push(`${bar} ${passRate}%`);
  lines.push('```');
  lines.push('');

  // ========== 结果摘要 ==========
  if (failed === 0) {
    lines.push('## 🎉 测试结果：全部通过！');
    lines.push('');
    lines.push('所有测试用例均已成功执行，未发现任何问题。');
    lines.push('');
  } else {
    lines.push('## ⚠️ 测试结果：存在失败用例');
    lines.push('');
    lines.push(`共有 **${failed}** 个测试用例执行失败，请查看下方详情。`);
    lines.push('');
  }

  // ========== 分类统计 ==========
  lines.push('## 📂 模块测试统计');
  lines.push('');

  // 按 suiteTitle 分组
  const moduleMap = {};
  for (const test of allTests) {
    if (!moduleMap[test.suiteTitle]) {
      moduleMap[test.suiteTitle] = { total: 0, passed: 0, failed: 0, tests: [] };
    }
    moduleMap[test.suiteTitle].total++;
    moduleMap[test.suiteTitle].tests.push(test);
    if (test.status === 'expected') moduleMap[test.suiteTitle].passed++;
    else if (test.status === 'unexpected') moduleMap[test.suiteTitle].failed++;
  }

  lines.push('| 模块 | 总数 | 通过 | 失败 | 通过率 |');
  lines.push('|------|------|------|------|--------|');
  for (const [module, stats] of Object.entries(moduleMap)) {
    const rate = stats.total > 0 ? Math.round((stats.passed / stats.total) * 100) : 0;
    const emoji = stats.failed === 0 ? '✅' : '❌';
    lines.push(`| ${emoji} ${module} | ${stats.total} | ${stats.passed} | ${stats.failed} | ${rate}% |`);
  }
  lines.push('');

  // ========== 详细测试结果 ==========
  lines.push('## 📋 详细测试结果');
  lines.push('');

  for (const [module, stats] of Object.entries(moduleMap)) {
    lines.push(`### ${module}`);
    lines.push('');

    lines.push('| 状态 | 测试用例 | 耗时 |');
    lines.push('|------|----------|------|');

    for (const test of stats.tests) {
      const status = test.status === 'expected' ? 'passed' : 'failed';
      const emoji = getStatusEmoji(status);
      const duration = test.results?.[0]?.duration
        ? formatDuration(test.results[0].duration)
        : 'N/A';

      lines.push(`| ${emoji} | ${test.title} | ${duration} |`);
    }
    lines.push('');

    // 失败的用例显示错误详情
    const failedTests = stats.tests.filter(t => t.status === 'unexpected');
    if (failedTests.length > 0) {
      for (const test of failedTests) {
        const error = test.results?.[0]?.error?.message || '';
        if (error) {
          lines.push(`<details>`);
          lines.push(`<summary>🔴 <b>${test.title}</b> - 错误详情</summary>`);
          lines.push('');
          lines.push('```');
          lines.push(truncateError(error, 500));
          lines.push('```');
          lines.push('');
          lines.push('</details>');
          lines.push('');
        }
      }
    }
  }

  // ========== 执行环境信息 ==========
  lines.push('## 🖥️ 执行环境');
  lines.push('');
  lines.push('| 项目 | 详情 |');
  lines.push('|------|------|');
  lines.push(`| 🖥️ 运行环境 | ${process.env.CI ? 'GitHub Actions' : '本地'} |`);
  lines.push(`| 🌐 运行系统 | ${process.env.RUNNER_OS || process.platform} |`);
  lines.push(`| 📦 Node.js | ${process.version} |`);
  lines.push(`| 🎭 Playwright | ${getPlaywrightVersion()} |`);
  lines.push(`| 🔗 Action Run | [#${process.env.GITHUB_RUN_ID || 'N/A'}](${process.env.GITHUB_SERVER_URL || ''}/${process.env.GITHUB_REPOSITORY || ''}/actions/runs/${process.env.GITHUB_RUN_ID || ''}) |`);
  lines.push('');

  // ========== 页脚 ==========
  lines.push('---');
  lines.push('');
  lines.push(`*本报告由自动化测试系统自动生成 · ${formatDateTime()}*`);

  return lines.join('\n');
}

function getPlaywrightVersion() {
  try {
    const pkg = require('@playwright/test/package.json');
    return pkg.version || 'unknown';
  } catch {
    return 'unknown';
  }
}

// ============================================================
// 主函数
// ============================================================

function main() {
  console.log('📊 正在生成测试报告...');

  const reportData = parseReport();
  const markdown = generateReport(reportData);

  fs.writeFileSync(REPORT_CONFIG.outputPath, markdown, 'utf-8');

  console.log(`✅ 报告已生成: ${REPORT_CONFIG.outputPath}`);

  // 同时输出简要统计到控制台
  if (reportData) {
    const allTests = [];
    function collect(suite) {
      if (suite.specs) {
        for (const spec of suite.specs) {
          if (spec.tests) allTests.push(...spec.tests);
        }
      }
      if (suite.suites) {
        for (const child of suite.suites) collect(child);
      }
    }
    for (const suite of reportData.suites || []) collect(suite);

    const passed = allTests.filter(t => t.status === 'expected').length;
    console.log(`📈 统计: ${allTests.length} 个测试, ${passed} 通过, ${allTests.length - passed} 失败`);
  }
}

main();
