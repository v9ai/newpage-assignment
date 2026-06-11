// Records a short demo of the running app (http://localhost:3000) to docs/media/.
// Usage: node scripts/record-demo.mjs   (stack must be up: docker compose up)
import { chromium } from 'playwright'
import { mkdirSync, renameSync, readdirSync } from 'node:fs'
import { join } from 'node:path'

const BASE_URL = process.env.DEMO_URL ?? 'http://localhost:3000'
const ROOT = join(import.meta.dirname, '..', '..')
const OUT_DIR = join(ROOT, 'docs', 'media')
const VIDEO_DIR = join(OUT_DIR, '.raw')
const SAMPLE = join(ROOT, 'samples', 'docs', '03-entity-resolution.md')

mkdirSync(VIDEO_DIR, { recursive: true })

const browser = await chromium.launch()
const context = await browser.newContext({
  viewport: { width: 1280, height: 800 },
  recordVideo: { dir: VIDEO_DIR, size: { width: 1280, height: 800 } },
})
const page = await context.newPage()

await page.goto(BASE_URL, { waitUntil: 'networkidle' })
await page.waitForSelector('text=system status', { timeout: 15000 })
await page.waitForTimeout(1500)

// Walk the health chips so the cursor tells the story
for (const service of ['Postgres', 'Qdrant', 'Openai']) {
  const chip = page.locator(`text=${service}`).first()
  await chip.hover().catch(() => {})
  await page.waitForTimeout(700)
}

// Upload a sample through the real input and watch ingestion progress
const input = page.locator('input[type="file"]').first()
await input.setInputFiles(SAMPLE)
await page.waitForTimeout(2000) // toast + Ingesting badge
await page
  .waitForSelector('text=Ready', { timeout: 90000 })
  .catch(() => console.warn('ingestion did not reach Ready in time — recording anyway'))
await page.waitForTimeout(1500)

// Ask a question about the uploaded doc and let the cited answer stream in
const composer = page.locator('textarea, input[type="text"]').last()
await composer.fill('How does entity resolution decide when two records are the same company?')
await composer.press('Enter')
await page.waitForTimeout(30000) // token stream + citations
const chip = page.locator('button:has-text("entity-resolution")').last()
await chip.hover().catch(() => {})
await page.waitForTimeout(1500)
await chip.click().catch(() => {})
await page.waitForTimeout(2500) // source preview open
await page.keyboard.press('Escape')
await page.waitForTimeout(1000)

await context.close() // flushes the video
await browser.close()

// Playwright names the file with a hash — move it to a stable path
const raw = readdirSync(VIDEO_DIR).find((f) => f.endsWith('.webm'))
if (!raw) throw new Error('no video produced')
renameSync(join(VIDEO_DIR, raw), join(OUT_DIR, 'demo.webm'))
console.log('saved docs/media/demo.webm')
