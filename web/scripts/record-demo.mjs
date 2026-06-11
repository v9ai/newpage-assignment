// Records the full-feature demo of the running app (http://localhost:3000) to docs/media/.
// Usage: node scripts/record-demo.mjs   (stack must be up: docker compose up)
//
// Flow: health tour -> rejected upload (error toast) -> upload -> Ingesting -> Ready
//       -> cited answer -> source preview -> follow-up turn -> reload restores session.
import { chromium } from 'playwright'
import { mkdirSync, rmSync } from 'node:fs'
import { join } from 'node:path'

const BASE_URL = process.env.DEMO_URL ?? 'http://localhost:3000'
const ROOT = join(import.meta.dirname, '..', '..')
const OUT_DIR = join(ROOT, 'docs', 'media')
const VIDEO_DIR = join(OUT_DIR, '.raw')
const SAMPLE = join(ROOT, 'samples', 'docs', '03-entity-resolution.md')

const QUESTION =
  'How does entity resolution decide when two records are the same company?'
const FOLLOW_UP =
  'What happens when two candidate records score close to the match threshold?'
const CHIP_SELECTOR = 'button:has-text("entity-resolution")'

// Start from a clean corpus so the recording shows real ingestion progress
// instead of an already-Ready document. Sessions are kept (no DELETE endpoint);
// the script opens a fresh chat via the UI's "New" action instead.
const docs = await (await fetch(`${BASE_URL}/api/documents`)).json()
for (const doc of docs) {
  await fetch(`${BASE_URL}/api/documents/${doc.id}`, { method: 'DELETE' })
}
if (docs.length) console.log(`reset: deleted ${docs.length} existing document(s)`)

rmSync(VIDEO_DIR, { recursive: true, force: true }) // stale webms from old runs
mkdirSync(VIDEO_DIR, { recursive: true })

const browser = await chromium.launch()
const context = await browser.newContext({
  viewport: { width: 1280, height: 800 },
  recordVideo: { dir: VIDEO_DIR, size: { width: 1280, height: 800 } },
})
const page = await context.newPage()
const video = page.video()

await page.goto(BASE_URL, { waitUntil: 'networkidle' })
await page.waitForSelector('text=system status', { timeout: 15000 })
await page.waitForTimeout(1500)

// Walk the health chips so the cursor tells the story
for (const service of ['Postgres', 'Qdrant', 'Openai']) {
  const chip = page.locator(`text=${service}`).first()
  await chip.hover().catch(() => {})
  await page.waitForTimeout(700)
}

// Fresh conversation so restored history from earlier sessions stays off screen
await page
  .getByRole('button', { name: 'New' })
  .click()
  .catch(() => console.warn('no New-chat button — continuing in restored session'))
await page.waitForTimeout(800)

// Try an unsupported file first — the precheck rejects it with an error toast
const input = page.locator('input[type="file"]').first()
await input.setInputFiles({
  name: 'quarterly-report.exe',
  mimeType: 'application/octet-stream',
  buffer: Buffer.from('not a document'),
})
await page
  .waitForSelector("text=Can't upload", { timeout: 5000 })
  .catch(() => console.warn('rejection toast did not appear — recording anyway'))
await page.waitForTimeout(2500) // let the toast read on video

// Upload a sample through the real input and watch ingestion progress
await input.setInputFiles(SAMPLE)
await page.waitForTimeout(2000) // toast + Ingesting badge
await page
  .waitForSelector('text=Ready', { timeout: 90000 })
  .catch(() => console.warn('ingestion did not reach Ready in time — recording anyway'))
await page.waitForTimeout(1500)

// Ask a question about the uploaded doc and let the cited answer stream in.
// Citation chips arrive with the stream's final `citations` event, so a chip
// on screen means the turn finished.
const composer = page.locator('textarea, input[type="text"]').last()
await composer.fill(QUESTION)
await composer.press('Enter')
await page
  .waitForSelector(CHIP_SELECTOR, { timeout: 120000 })
  .catch(() => console.warn('no citation chip after first turn — recording anyway'))
await page.waitForTimeout(1500)
const chip = page.locator(CHIP_SELECTOR).last()
await chip.hover().catch(() => {})
await page.waitForTimeout(1500)
await chip.click().catch(() => {})
await page.waitForTimeout(2500) // source preview open
await page.keyboard.press('Escape')
await page.waitForTimeout(1000)

// Follow-up question in the same session — multi-turn history on screen.
// Polled, since :has-text() can't run inside waitForFunction.
const chipsBefore = await page.locator(CHIP_SELECTOR).count()
await composer.fill(FOLLOW_UP)
await composer.press('Enter')
const followUpDeadline = Date.now() + 120000
while (Date.now() < followUpDeadline) {
  if ((await page.locator(CHIP_SELECTOR).count()) > chipsBefore) break
  await page.waitForTimeout(1000)
}
if ((await page.locator(CHIP_SELECTOR).count()) <= chipsBefore)
  console.warn('no citation chip after follow-up — recording anyway')
await page.waitForTimeout(2000)

// Reload: the newest session auto-restores from the DB, citations included.
// Wait for the follow-up turn — the first question may be scrolled out of view.
await page.reload({ waitUntil: 'networkidle' }).catch(() => {})
await page
  .waitForSelector(`text=${FOLLOW_UP}`, { timeout: 20000 })
  .catch(() => console.warn('restored conversation did not appear — recording anyway'))
await page.waitForTimeout(1500)
await page.locator(CHIP_SELECTOR).last().hover().catch(() => {})
await page.waitForTimeout(2000)

// saveAs() follows the file the recorder actually wrote, even if the encoder
// restarted mid-run and video.path() points elsewhere.
await context.close() // flushes the video
await video.saveAs(join(OUT_DIR, 'demo.webm'))
await browser.close()
console.log('saved docs/media/demo.webm')
