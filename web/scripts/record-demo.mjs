// Records a short demo of the running app (http://localhost:3000) to docs/media/.
// Usage: node scripts/record-demo.mjs   (stack must be up: docker compose up)
import { chromium } from 'playwright'
import { mkdirSync, renameSync, readdirSync } from 'node:fs'
import { join } from 'node:path'

const BASE_URL = process.env.DEMO_URL ?? 'http://localhost:3000'
const OUT_DIR = join(import.meta.dirname, '..', '..', 'docs', 'media')
const VIDEO_DIR = join(OUT_DIR, '.raw')

mkdirSync(VIDEO_DIR, { recursive: true })

const browser = await chromium.launch()
const context = await browser.newContext({
  viewport: { width: 1280, height: 800 },
  recordVideo: { dir: VIDEO_DIR, size: { width: 1280, height: 800 } },
})
const page = await context.newPage()

await page.goto(BASE_URL, { waitUntil: 'networkidle' })
await page.waitForSelector('text=System status')
await page.waitForTimeout(1500)

// Walk the health rows so the cursor tells the story
for (const service of ['postgres', 'qdrant', 'openai']) {
  await page.hover(`li:has-text("${service}")`)
  await page.waitForTimeout(900)
}
await page.hover('button:has-text("Upload documents")')
await page.waitForTimeout(1500)

await context.close() // flushes the video
await browser.close()

// Playwright names the file with a hash — move it to a stable path
const raw = readdirSync(VIDEO_DIR).find((f) => f.endsWith('.webm'))
if (!raw) throw new Error('no video produced')
renameSync(join(VIDEO_DIR, raw), join(OUT_DIR, 'demo.webm'))
console.log('saved docs/media/demo.webm')
