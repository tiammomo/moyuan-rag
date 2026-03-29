import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { chromium } from 'playwright';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const frontendRoot = path.resolve(__dirname, '..');
const repoRoot = path.resolve(frontendRoot, '..');
const backendEnvPath = path.join(repoRoot, 'backend', '.env');

function parseArgs(argv) {
  const args = {};

  for (let index = 0; index < argv.length; index += 1) {
    const current = argv[index];
    if (!current.startsWith('--')) {
      continue;
    }

    const trimmed = current.slice(2);
    if (trimmed.includes('=')) {
      const [key, value] = trimmed.split(/=(.*)/s, 2);
      args[key] = value;
      continue;
    }

    const next = argv[index + 1];
    if (!next || next.startsWith('--')) {
      args[trimmed] = 'true';
      continue;
    }

    args[trimmed] = next;
    index += 1;
  }

  return args;
}

function readEnvFile(filePath) {
  if (!fs.existsSync(filePath)) {
    return {};
  }

  const content = fs.readFileSync(filePath, 'utf8');
  const values = {};

  for (const rawLine of content.split(/\r?\n/)) {
    const line = rawLine.trim();
    if (!line || line.startsWith('#')) {
      continue;
    }

    const separatorIndex = line.indexOf('=');
    if (separatorIndex === -1) {
      continue;
    }

    const key = line.slice(0, separatorIndex).trim();
    const value = line.slice(separatorIndex + 1).trim();
    values[key] = value;
  }

  return values;
}

function resolveBoolean(value, fallback = false) {
  if (value === undefined) {
    return fallback;
  }

  return ['1', 'true', 'yes', 'on'].includes(String(value).toLowerCase());
}

function ensureDirectory(dirPath) {
  fs.mkdirSync(dirPath, { recursive: true });
}

function timestampSegment() {
  const now = new Date();
  const pad = (value) => String(value).padStart(2, '0');
  return [
    now.getFullYear(),
    pad(now.getMonth() + 1),
    pad(now.getDate()),
    '-',
    pad(now.getHours()),
    pad(now.getMinutes()),
    pad(now.getSeconds()),
  ].join('');
}

async function assertResponseOk(response, label) {
  if (!response || !response.ok()) {
    const status = response ? response.status() : 'no-response';
    throw new Error(`${label} returned ${status}`);
  }
}

async function saveScreenshot(page, outputDir, fileName) {
  const filePath = path.join(outputDir, fileName);
  await page.screenshot({ path: filePath, fullPage: true });
  return filePath;
}

async function main() {
  const cliArgs = parseArgs(process.argv.slice(2));
  const localEnv = readEnvFile(backendEnvPath);

  const baseUrl = cliArgs['base-url'] || process.env.PLAYWRIGHT_SMOKE_BASE_URL || 'http://localhost:33004';
  const apiUrl = cliArgs['api-url'] || process.env.PLAYWRIGHT_SMOKE_API_URL || 'http://localhost:38084';
  const username =
    cliArgs.username ||
    process.env.PLAYWRIGHT_SMOKE_USERNAME ||
    localEnv.PLAYWRIGHT_SMOKE_USERNAME ||
    localEnv.DEFAULT_ADMIN_USERNAME;
  const password =
    cliArgs.password ||
    process.env.PLAYWRIGHT_SMOKE_PASSWORD ||
    localEnv.PLAYWRIGHT_SMOKE_PASSWORD ||
    localEnv.DEFAULT_ADMIN_PASSWORD;
  const outputDir =
    cliArgs['output-dir'] ||
    process.env.PLAYWRIGHT_SMOKE_OUTPUT_DIR ||
    path.join(frontendRoot, 'test-results', 'playwright-smoke', timestampSegment());
  const headed = resolveBoolean(cliArgs.headed || process.env.PLAYWRIGHT_SMOKE_HEADED, false);

  if (!username || !password) {
    throw new Error(
      'Missing smoke credentials. Set PLAYWRIGHT_SMOKE_USERNAME / PLAYWRIGHT_SMOKE_PASSWORD or provide DEFAULT_ADMIN_* in backend/.env.',
    );
  }

  ensureDirectory(outputDir);

  const summary = {
    started_at: new Date().toISOString(),
    base_url: baseUrl,
    api_url: apiUrl,
    username,
    output_dir: path.relative(frontendRoot, outputDir),
    steps: [],
  };

  const browser = await chromium.launch({ headless: !headed });
  const context = await browser.newContext({
    viewport: { width: 1440, height: 960 },
  });
  const page = await context.newPage();

  const runStep = async (name, action, screenshotName) => {
    const step = {
      name,
      started_at: new Date().toISOString(),
      status: 'running',
      screenshot: null,
    };
    summary.steps.push(step);

    try {
      await action();
      if (screenshotName) {
        step.screenshot = path.relative(frontendRoot, await saveScreenshot(page, outputDir, screenshotName));
      }
      step.status = 'passed';
    } catch (error) {
      if (screenshotName) {
        step.screenshot = path.relative(
          frontendRoot,
          await saveScreenshot(page, outputDir, `failed-${screenshotName}`),
        );
      }
      step.status = 'failed';
      step.error = error instanceof Error ? error.message : String(error);
      throw error;
    } finally {
      step.finished_at = new Date().toISOString();
    }
  };

  try {
    await runStep(
      'backend-health',
      async () => {
        const response = await page.request.get(`${apiUrl}/health`);
        const payload = await response.json();
        if (!response.ok() || payload.status !== 'healthy') {
          throw new Error(`Backend health failed with status ${response.status()}`);
        }
      },
      '00-backend-health.png',
    );

    await runStep(
      'login-page',
      async () => {
        const response = await page.goto(`${baseUrl}/auth/login`, { waitUntil: 'networkidle' });
        await assertResponseOk(response, 'Login page');
        await page.getByRole('heading', { name: '登录账户' }).waitFor();
      },
      '01-login-page.png',
    );

    await runStep(
      'login-submit',
      async () => {
        await page.getByLabel('用户名或邮箱').fill(username);
        await page.getByLabel('密码').fill(password);
        await Promise.all([
          page.waitForURL(/\/chat(?:\?.*)?$/),
          page.getByRole('button', { name: '登录' }).click(),
        ]);
        await page.getByRole('button', { name: '新对话' }).waitFor();
      },
      '02-chat-page.png',
    );

    await runStep(
      'knowledge-page',
      async () => {
        const response = await page.goto(`${baseUrl}/knowledge`, { waitUntil: 'networkidle' });
        await assertResponseOk(response, 'Knowledge page');
        await page.getByRole('heading', { name: '知识库管理' }).waitFor();
      },
      '03-knowledge-page.png',
    );

    await runStep(
      'skills-page',
      async () => {
        const response = await page.goto(`${baseUrl}/skills`, { waitUntil: 'networkidle' });
        await assertResponseOk(response, 'Skills page');
        await page.getByRole('heading', { name: 'Skills' }).waitFor();
      },
      '04-skills-page.png',
    );

    await runStep(
      'admin-skills-page',
      async () => {
        const response = await page.goto(`${baseUrl}/admin/skills`, { waitUntil: 'networkidle' });
        await assertResponseOk(response, 'Admin skills page');
        await page.getByRole('heading', { name: '安装任务', exact: true }).waitFor();
        await page.getByRole('heading', { name: '发起远端安装', exact: true }).waitFor();
      },
      '05-admin-skills-page.png',
    );

    summary.status = 'passed';
  } catch (error) {
    summary.status = 'failed';
    summary.error = error instanceof Error ? error.message : String(error);
    throw error;
  } finally {
    summary.finished_at = new Date().toISOString();
    fs.writeFileSync(
      path.join(outputDir, 'summary.json'),
      `${JSON.stringify(summary, null, 2)}\n`,
      'utf8',
    );
    await context.close();
    await browser.close();
  }
}

main().catch((error) => {
  console.error(`[playwright-smoke] ${error instanceof Error ? error.message : String(error)}`);
  process.exitCode = 1;
});
