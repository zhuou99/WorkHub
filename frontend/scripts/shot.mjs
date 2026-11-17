/** 用 Playwright 登录并截工作台，用来肉眼核对视觉。
 *  node scripts/shot.mjs [输出路径]
 * 需要前后端都在跑：后端 5277、前端 5173。
 */
import { chromium } from 'playwright'

const OUT = process.argv[2] ?? 'dashboard.png'
const FRONT = process.env.WORKHUB_FRONT ?? 'http://127.0.0.1:5173'
const EDGE = 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'

const browser = await chromium.launch({ executablePath: EDGE })
// 固定视口，截首屏（不整页），尺寸可控、便于查看
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

const errors = []
page.on('console', (m) => m.type() === 'error' && errors.push(m.text()))
page.on('pageerror', (e) => errors.push(String(e)))

await page.goto(FRONT, { waitUntil: 'networkidle' })
if (await page.locator('#username').count()) {
  await page.fill('#username', 'admin')
  await page.fill('#password', 'admin123')
  await page.click('button[type=submit]')
  await page.waitForSelector('.app-shell', { timeout: 15000 })
  await page.waitForTimeout(800)
}
await page.screenshot({ path: OUT, type: 'jpeg', quality: 85 })

console.log(`截图已存：${OUT}`)
if (errors.length) {
  console.log('页面报错：')
  for (const e of errors) console.log('  ' + e)
  process.exitCode = 1
} else {
  console.log('无控制台报错')
}
await browser.close()
