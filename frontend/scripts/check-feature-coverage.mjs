/**
 * Feature Coverage Sync Check
 *
 * Reads docs/FEATURES.md, extracts all feature IDs with status "implemented" or "tested",
 * then verifies that each feature has at least one corresponding test file on disk.
 *
 * Exit code 1 if any feature lacks test coverage.
 * Run in CI: node scripts/check-feature-coverage.mjs
 */

import { readFileSync, existsSync } from 'fs'
import { resolve } from 'path'

const FEATURES_PATH = resolve('..', 'docs', 'FEATURES.md')

if (!existsSync(FEATURES_PATH)) {
  console.log('No docs/FEATURES.md found — skipping feature coverage check.')
  process.exit(0)
}

const content = readFileSync(FEATURES_PATH, 'utf-8')

// Parse feature blocks: ### F-XXX: Name ... - **Status:** ... - **Test Files:** ...
const featureRegex = /### (F-\d{3}): (.+)\n([\s\S]*?)(?=\n### F-|\n---|\n<!-- |$)/g
const statusRegex = /\*\*Status:\*\*\s*(planned|implemented|tested)/
const testFileRegex = /(?:Unit|E2E|Integration|Component|A11y):\s*`([^`]+)`/g

let failures = 0
let checked = 0
let match

while ((match = featureRegex.exec(content)) !== null) {
  const [, id, name, body] = match
  const statusMatch = body.match(statusRegex)

  if (!statusMatch) continue

  const status = statusMatch[1]

  // Only check features that are implemented or tested
  if (status === 'planned') continue

  checked++

  // Extract all test file paths
  const testFiles = []
  let tfMatch
  while ((tfMatch = testFileRegex.exec(body)) !== null) {
    testFiles.push(tfMatch[1])
  }

  if (testFiles.length === 0) {
    console.error(`FAIL  ${id}: ${name} — status is "${status}" but no test files listed`)
    failures++
    continue
  }

  // Verify each test file exists on disk
  const missing = testFiles.filter((f) => !existsSync(resolve(f)))

  if (missing.length > 0) {
    console.error(
      `FAIL  ${id}: ${name} — test files not found on disk:\n` +
        missing.map((f) => `        ${f}`).join('\n')
    )
    failures++
  } else {
    console.log(`PASS  ${id}: ${name} — ${testFiles.length} test file(s) verified`)
  }
}

console.log(`\n${checked} feature(s) checked, ${failures} failure(s)`)

if (failures > 0) {
  console.error(
    '\nFeature coverage check failed. Every implemented feature must have test files.\n' +
      'Update docs/FEATURES.md with test file paths, or write the missing tests.'
  )
  process.exit(1)
}
