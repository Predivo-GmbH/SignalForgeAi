import { chromium } from 'playwright';
import { mkdirSync } from 'fs';

const BASE = 'http://localhost:5173';
const DIR = './test-screenshots';
mkdirSync(DIR, { recursive: true });

const pages = [
  // Auth pages (public)
  ['01-login', '/login'],
  ['02-signup', '/signup'],
  ['03-forgot-password', '/forgot-password'],
  ['04-reset-password', '/reset-password'],

  // Authenticated pages
  ['05-dashboard-top', '/'],
  ['06-dashboard-bottom', '/', { scrollToBottom: true }],
  ['07-advisor', '/advisor'],
  ['08-strategies', '/strategies'],
  ['09-backtest', '/backtest'],
  ['10-trades-top', '/trades'],
  ['11-trades-bottom', '/trades', { scrollToBottom: true }],
  ['12-analytics-top', '/analytics'],
  ['13-analytics-bottom', '/analytics', { scrollToBottom: true }],
  ['14-risk', '/risk'],
  ['15-engine-top', '/engine'],
  ['16-engine-bottom', '/engine', { scrollToBottom: true }],
  ['17-settings-profile', '/settings'],
  ['18-settings-bottom', '/settings', { scrollToBottom: true }],
];

async function screenshotPage(context, name, path, opts = {}) {
  const page = await context.newPage();
  try {
    await page.goto(`${BASE}${path}`, { waitUntil: 'networkidle', timeout: 15000 });
    await page.waitForTimeout(800);
    if (opts.scrollTo) {
      await page.evaluate((y) => window.scrollTo(0, y), opts.scrollTo);
      await page.waitForTimeout(400);
    } else if (opts.scrollToBottom) {
      await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
      await page.waitForTimeout(400);
    }
    await page.screenshot({ path: `${DIR}/${name}.png`, fullPage: false });
    console.log(`  OK  ${name}`);
  } catch (e) {
    console.log(`  FAIL  ${name}: ${e.message.split('\n')[0]}`);
  }
  await page.close();
}

(async () => {
  console.log('Launching browser (430x932, dark mode)...');
  const browser = await chromium.launch();
  const ctx = await browser.newContext({
    viewport: { width: 430, height: 932 },
    colorScheme: 'dark',
  });

  for (const [name, path, opts] of pages) {
    await screenshotPage(ctx, name, path, opts);
  }

  await ctx.close();
  await browser.close();
  console.log(`\nDone. Screenshots saved to ${DIR}/`);
})();
