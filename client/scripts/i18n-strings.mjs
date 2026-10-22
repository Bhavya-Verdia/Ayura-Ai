// Read every `tr('ui.…', 'English')` call and `<Trans>` in src/ into locales/en-ui.json.
//
// en-ui.json is for tooling only and is not bundled: the English is already the
// default at every call, so shipping it again in en.json cost 31 kB of startup JS.
//
//   node scripts/i18n-strings.mjs           # write en-ui.json
//   node scripts/i18n-strings.mjs --check   # exit 1 if it is not what the source says
//
// The English lives at the call (lib/tr.js), so the source is the truth and en-ui.json
// is generated from it. A key used twice with two different defaults is an error.
// `server/scripts/translate_ui.py` fills the other locales from it.
import { readFileSync, writeFileSync, readdirSync, statSync } from 'node:fs'
import { join, resolve, dirname } from 'node:path'
import { parse } from '@babel/parser'
import _traverse from '@babel/traverse'

const traverse = _traverse.default || _traverse
const ROOT = resolve(dirname(new URL(import.meta.url).pathname), '..')
const SRC = join(ROOT, 'src')
const EN = join(SRC, 'locales', 'en-ui.json')

function* files(dir) {
  for (const name of readdirSync(dir)) {
    const p = join(dir, name)
    if (name === 'locales' || name === 'node_modules') continue
    if (statSync(p).isDirectory()) yield* files(p)
    else if (/\.(jsx?|mjs)$/.test(name)) yield p
  }
}

export function extract() {
  const out = {}
  for (const file of files(SRC)) {
    const src = readFileSync(file, 'utf8')
    if (!src.includes('tr(') && !src.includes('<Trans')) continue
    const ast = parse(src, { sourceType: 'module', plugins: ['jsx'] })
    const add = (key, text) => {
      if (!key.startsWith('ui.')) return
      if (key in out && out[key] !== text)
        throw new Error(`${key} has two English defaults:\n  ${out[key]}\n  ${text}`)
      out[key] = text
    }
    traverse(ast, {
      // <Trans i18nKey="ui.…" defaults={"…"} /> — a sentence with markup or values.
      JSXOpeningElement(path) {
        if (path.node.name.name !== 'Trans') return
        const attr = (n) => path.node.attributes.find((a) => a.name?.name === n)?.value
        const k = attr('i18nKey'), d = attr('defaults')
        const text = d?.type === 'StringLiteral' ? d.value
          : d?.type === 'JSXExpressionContainer' && d.expression.type === 'StringLiteral' ? d.expression.value : null
        if (k?.type === 'StringLiteral' && text != null) add(k.value, text)
      },
      CallExpression(path) {
        const { callee, arguments: args } = path.node
        if (callee.type !== 'Identifier' || callee.name !== 'tr') return
        const [k, d] = args
        if (k?.type !== 'StringLiteral' || d?.type !== 'StringLiteral') return
        add(k.value, d.value)
      },
    })
  }
  return out
}

export function nest(flat) {
  const tree = {}
  for (const key of Object.keys(flat).sort()) {
    const parts = key.split('.')
    let node = tree
    for (const p of parts.slice(0, -1)) node = node[p] ??= {}
    node[parts[parts.length - 1]] = flat[key]
  }
  return tree
}

if (process.argv[1]?.endsWith('i18n-strings.mjs')) {
  const strings = extract()
  const next = { ui: nest(strings).ui }
  const text = JSON.stringify(next, null, 2) + '\n'
  if (process.argv.includes('--check')) {
    if (readFileSync(EN, 'utf8') !== text) {
      console.error('locales/en-ui.json is out of date: run node scripts/i18n-strings.mjs')
      process.exit(1)
    }
    console.log(`en-ui.json: ${Object.keys(strings).length} strings, in sync`)
  } else {
    writeFileSync(EN, text)
    console.log(`en-ui.json: ${Object.keys(strings).length} strings written`)
  }
}
