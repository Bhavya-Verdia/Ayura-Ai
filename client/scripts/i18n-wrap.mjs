// Wrap a screen's hard-coded English in `tr('ns.key', 'English')` calls.
//
//   node scripts/i18n-wrap.mjs src/pages/Settings.jsx [more files…]   # rewrite in place
//   node scripts/i18n-wrap.mjs --dry src/pages/Settings.jsx           # report only
//
// The file is parsed (Babel) only to find exact source ranges; the edits are spliced
// into the original text, so nothing else in the file is reformatted. What it wraps:
//
//   - JSX text:                         <p>Save your plan</p>
//   - display attributes:               placeholder="…" title="…" aria-label="…" alt="…" label="…"
//   - string/template literals rendered as children or display attributes:
//                                       {saving ? 'Saving…' : 'Save'}  {`Week ${n}`}
//   - toast / confirm / setError-style messages
//   - display properties of object literals (label, desc, hint, title, …). At module
//     level they become getters, so the string is looked up when it is rendered and
//     not once, in English, when the module loads.
//
// Text mixed with expressions in one JSX text run ("Hello {name}, welcome") is left
// and reported, because translating the fragments separately reads badly. The keys are
// `<file namespace>.<camelCase of the first words>`; `scripts/i18n-strings.mjs` reads
// every `tr(` call back out into the locale files.
import { readFileSync, writeFileSync } from 'node:fs'
import { basename, dirname, relative, resolve } from 'node:path'
import { parse } from '@babel/parser'
import _traverse from '@babel/traverse'

const traverse = _traverse.default || _traverse
const SRC = resolve(dirname(new URL(import.meta.url).pathname), '../src')

const DISPLAY_ATTRS = new Set(['placeholder', 'title', 'alt', 'aria-label', 'aria-description',
  'label', 'description', 'subtitle', 'hint', 'message', 'heading', 'emptyText', 'confirmLabel'])
const DISPLAY_PROPS = new Set(['label', 'desc', 'description', 'hint', 'title', 'subtitle',
  'placeholder', 'help', 'helper', 'tagline', 'caption', 'empty', 'emptyText', 'body', 'blurb',
  'question', 'cta', 'tip', 'note', 'text', 'message', 'heading', 'short', 'long', 'detail', 'sub'])
const MESSAGE_CALLS = /^(toast(\.(success|error|info|warning|message|loading))?|confirm|window\.confirm|alert|setError|setErr|setMessage|setMsg|setStatusMsg|setNotice|setInfo|setSuccess|setWarning)$/

// Not prose: identifiers, class names, translation keys ('landing.how1_title' — the
// landing page keeps keys in its tables), URLs and paths.
const isProse = (s) => /[A-Za-z]{2,}/.test(s) && !/^[a-z0-9_-]+$/.test(s.trim()) &&
  !/^[\w-]+(\.[\w-]+)+$/.test(s.trim()) &&
  !/^(https?:|\/|#|\.|mailto:)/.test(s.trim()) && !/^[A-Z0-9_]+$/.test(s.trim())

const ENTITIES = { apos: "'", quot: '"', amp: '&', nbsp: '\u00a0', lt: '<', gt: '>', mdash: '—',
  ndash: '–', hellip: '…', middot: '·', rarr: '→', larr: '←', rsquo: '\u2019', lsquo: '\u2018',
  rdquo: '\u201d', ldquo: '\u201c', times: '×', deg: '°', bull: '•', copy: '©', trade: '™' }
// JSX decodes entities in text and attribute strings; the default string must hold
// the character, or "You&rsquo;re" is printed as written.
const decode = (s) => s.replace(/&([a-zA-Z]+);/g, (m, n) => ENTITIES[n] ?? m)
  .replace(/&#(\d+);/g, (m, d) => String.fromCodePoint(Number(d)))
  .replace(/&#x([0-9a-f]+);/gi, (m, h) => String.fromCodePoint(parseInt(h, 16)))
const quote = (s) => `'${s.replace(/\\/g, '\\\\').replace(/'/g, "\\'").replace(/\n/g, '\\n')}'`

function namespace(file) {
  const b = basename(file).replace(/\.(jsx?|mjs)$/, '')
  // Under `ui.` so no screen namespace collides with the flat keys the sidebar uses
  // (`settings`, `timeline`, `chat` are strings in the locale files).
  return 'ui.' + b.charAt(0).toLowerCase() + b.slice(1)
}

function slug(text) {
  const words = text.replace(/\{\{[^}]*\}\}/g, ' ').match(/[A-Za-z0-9]+/g) || ['text']
  const s = words.slice(0, 5).map((w, i) => (i ? w.charAt(0).toUpperCase() + w.slice(1).toLowerCase() : w.toLowerCase())).join('')
  return (/^[0-9]/.test(s) ? 'n' + s : s).slice(0, 40) || 'text'
}

function codeName(expr, src) {
  const raw = src.slice(expr.start, expr.end)
  const m = raw.match(/([A-Za-z_$][\w$]*)\s*(\)|\])?\s*$/)
  return (m ? m[1] : 'value').replace(/^\$/, '')
}

const INLINE = new Set(['strong', 'em', 'b', 'i', 'span', 'a', 'Link', 'code', 'br', 'small', 'u',
  'mark', 'abbr', 'sup', 'sub'])
const SIMPLE_EXPR = new Set(['Identifier', 'MemberExpression', 'OptionalMemberExpression', 'CallExpression',
  'OptionalCallExpression', 'ConditionalExpression', 'LogicalExpression', 'BinaryExpression',
  'TemplateLiteral', 'NumericLiteral'])

// JSX's own whitespace rule: a run containing a newline loses the line breaks and the
// indentation around them; a run on one line keeps its spaces.
function jsxText(raw) {
  const t = decode(raw)
  if (!t.includes('\n')) return t
  const lines = t.split('\n')
  return lines.map((l, i) => (i === 0 ? l.trimEnd() : i === lines.length - 1 ? l.trimStart() : l.trim()))
    .filter((l, i, a) => l || i === 0 || i === a.length - 1).join(' ').replace(/ {2,}/g, ' ')
}

export function wrapFile(file, { dry = false } = {}) {
  const src = readFileSync(file, 'utf8')
  const ast = parse(src, { sourceType: 'module', plugins: ['jsx'] })
  const ns = namespace(file)
  const keys = new Map()        // key -> text
  const byText = new Map()      // text -> key
  const edits = []
  let usesTrans = false
  const skipped = []

  const keyFor = (text) => {
    if (byText.has(text)) return byText.get(text)
    let k = slug(text), n = 2
    while (keys.has(k) && keys.get(k) !== text) k = slug(text) + n++
    keys.set(k, text); byText.set(text, `${ns}.${k}`)
    return `${ns}.${k}`
  }
  const call = (text, vars) => {
    const v = vars && vars.length ? `, { ${vars.map(([n, e]) => (n === e ? n : `${n}: ${e}`)).join(', ')} }` : ''
    return `tr(${quote(keyFor(text))}, ${quote(text)}${v})`
  }
  const shadowed = (path) => {
    const b = path.scope.getBinding('tr')
    return b && b.kind !== 'module'
  }
  const inFunction = (path) => Boolean(path.getFunctionParent())

  // A template literal with only simple expressions becomes interpolation.
  const template = (node) => {
    const vars = []
    let text = ''
    for (let i = 0; i < node.quasis.length; i++) {
      text += node.quasis[i].value.cooked
      if (i < node.expressions.length) {
        const e = node.expressions[i]
        if (!['Identifier', 'MemberExpression', 'OptionalMemberExpression', 'CallExpression', 'OptionalCallExpression',
          'ConditionalExpression', 'LogicalExpression', 'BinaryExpression'].includes(e.type)) return null
        let name = codeName(e, src)
        while (vars.some(([n, ex]) => n === name && ex !== src.slice(e.start, e.end))) name += '2'
        if (!vars.some(([n]) => n === name)) vars.push([name, src.slice(e.start, e.end)])
        text += `{{${name}}}`
      }
    }
    return isProse(text.replace(/\{\{[^}]*\}\}/g, '')) ? { text, vars } : null
  }

  const literal = (path) => {
    const n = path.node
    if (n.type === 'StringLiteral') return isProse(n.value) ? call(n.value) : null
    if (n.type === 'TemplateLiteral') {
      const t = template(n)
      return t ? call(t.text, t.vars) : null
    }
    return null
  }

  // Walk up through ?:, && and || only — anything else (a call, a comparison, an
  // object key) means the string is data, not text on screen.
  const renderedContext = (path) => {
    let p = path.parentPath
    let child = path
    while (p && (p.isConditionalExpression() && child.key !== 'test' || p.isLogicalExpression())) {
      child = p; p = p.parentPath
    }
    if (!p || !p.isJSXExpressionContainer()) return null
    const host = p.parentPath
    if (host.isJSXElement() || host.isJSXFragment()) return 'child'
    if (host.isJSXAttribute() && DISPLAY_ATTRS.has(host.node.name.name)) return 'attr'
    return null
  }

  traverse(ast, {
    // A sentence made of text, inline markup and values ("discover your <span>body
    // type</span>", "{n} exercises have") becomes one <Trans> sentence, so it is
    // translated whole and the translator can move the pieces.
    JSXElement(path) {
      const ch = path.node.children
      if (!ch.some((c) => c.type === 'JSXText' && isProse(jsxText(src.slice(c.start, c.end)).trim()))) return
      const meaningful = ch.filter((c) => !(c.type === 'JSXText' && !jsxText(src.slice(c.start, c.end)).trim()
        && src.slice(c.start, c.end).includes('\n')))
      if (!meaningful.some((c) => c.type !== 'JSXText')) return
      if (shadowed(path)) return
      // Already converted on an earlier run.
      if (/\btr\(|<Trans\b/.test(src.slice(path.node.start, path.node.end))) return
      const components = []
      const values = []
      let text = ''
      const valueName = (expr) => {
        let name = codeName(expr, src)
        const code = src.slice(expr.start, expr.end)
        if (name === 'value' || /^\d/.test(name)) name = 'value'
        while (values.some(([n, c]) => n === name && c !== code)) name += '2'
        if (!values.some(([n]) => n === name)) values.push([name, code])
        return `{{${name}}}`
      }
      for (const c of ch) {
        if (c.type === 'JSXText') { text += jsxText(src.slice(c.start, c.end)); continue }
        if (c.type === 'JSXExpressionContainer') {
          const e = c.expression
          if (e.type === 'JSXEmptyExpression') continue
          if (e.type === 'StringLiteral') { text += e.value; continue }
          if (!SIMPLE_EXPR.has(e.type)) return
          text += valueName(e)
          continue
        }
        if (c.type === 'JSXElement') {
          const name = c.openingElement.name.name
          // An element with no content of its own (an icon) can sit in a sentence as
          // a numbered tag; anything else with content is not inline text.
          const empty = c.openingElement.selfClosing || !c.children.length
          if (!INLINE.has(name) && !empty) return
          const open = src.slice(c.openingElement.start, c.openingElement.end).replace(/\s*\/?>$/, ' />')
          const idx = components.push(open) - 1
          if (c.openingElement.selfClosing || !c.children.length) { text += `<${idx}/>`; continue }
          let inner = ''
          for (const g of c.children) {
            if (g.type === 'JSXText') inner += jsxText(src.slice(g.start, g.end))
            else if (g.type === 'JSXExpressionContainer' && g.expression.type === 'StringLiteral') inner += g.expression.value
            else if (g.type === 'JSXExpressionContainer' && SIMPLE_EXPR.has(g.expression.type)) inner += valueName(g.expression)
            else return
          }
          text += `<${idx}>${inner.trim()}</${idx}>`
          continue
        }
        return
      }
      text = text.replace(/\s+/g, ' ').trim()
      if (!isProse(text.replace(/<\/?\d+\/?>|\{\{\w+\}\}/g, ' '))) return
      const key = keyFor(text)
      const vals = values.length ? ` values={{ ${values.map(([n, c]) => (n === c ? n : `${n}: ${c}`)).join(', ')} }}` : ''
      const comps = components.length ? ` components={[${components.join(', ')}]}` : ''
      const first = ch[0], last = ch[ch.length - 1]
      edits.push([first.start, last.end, `<Trans i18nKey=${JSON.stringify(key)} defaults={${JSON.stringify(text)}}${vals}${comps} />`])
      usesTrans = true
      path.skip()
    },
    JSXText(path) {
      const raw = src.slice(path.node.start, path.node.end)
      const text = decode(raw).replace(/\s+/g, ' ').trim()
      if (!isProse(text)) return
      const el = path.parentPath.node.openingElement?.name?.name
      if (['code', 'pre', 'style', 'script'].includes(el)) return
      // Text that runs straight into an expression on the same line is one sentence
      // split across nodes ("Hello {name}, welcome"); wrapping the pieces reads badly.
      const siblings = path.parentPath.node.children || []
      const i = siblings.indexOf(path.node)
      const touches = (c, side) => c && c.type === 'JSXExpressionContainer'
        && c.expression.type !== 'JSXEmptyExpression' && c.expression.type !== 'StringLiteral'
        && !(side === 'before' ? /\n\s*$/.test(src.slice(c.end, path.node.start) + raw.match(/^\s*/)[0])
          : /^\s*\n/.test(raw.match(/\s*$/)[0]))
      const mixed = touches(siblings[i - 1], 'before') || touches(siblings[i + 1], 'after')
      if (mixed) { skipped.push(`mixed text: ${text.slice(0, 60)}`); return }
      if (shadowed(path)) { skipped.push(`tr shadowed: ${text.slice(0, 40)}`); return }
      const lead = raw.match(/^\s*/)[0], trail = raw.match(/\s*$/)[0]
      // JSX keeps a lone space next to text on the same line; the expression keeps it explicitly.
      const keepLead = lead && !lead.includes('\n') ? "{' '}" : lead
      const keepTrail = trail && !trail.includes('\n') ? "{' '}" : trail
      edits.push([path.node.start, path.node.end, `${keepLead}{${call(text)}}${keepTrail}`])
    },
    JSXAttribute(path) {
      const name = path.node.name.name
      const v = path.node.value
      if (!DISPLAY_ATTRS.has(name) || !v || v.type !== 'StringLiteral' || !isProse(v.value)) return
      if (shadowed(path)) return
      edits.push([v.start, v.end, `{${call(decode(v.value))}}`])
    },
    'StringLiteral|TemplateLiteral'(path) {
      if (path.parentPath.isJSXAttribute()) return             // handled above
      if (path.parentPath.isTaggedTemplateExpression()) return
      if (path.parentPath.isImportDeclaration() || path.parentPath.isExportDeclaration()) return
      if (shadowed(path)) return
      // Already a translation call's argument.
      const parentCall = path.parentPath.isCallExpression() && src.slice(path.parentPath.node.callee.start, path.parentPath.node.callee.end)
      if (parentCall && /^(t|tr|i18n\.t)$/.test(parentCall)) return
      if (renderedContext(path)) {
        const r = literal(path); if (r) edits.push([path.node.start, path.node.end, r])
        return
      }
      // toast('…'), setError('…'), confirm('…') — the first argument.
      if (parentCall && MESSAGE_CALLS.test(parentCall) && path.key === 0) {
        const r = literal(path); if (r) edits.push([path.node.start, path.node.end, r])
        return
      }
      // { label: '…' } — a display property.
      const prop = path.parentPath
      if (prop.isObjectProperty() && path.key === 'value' && !prop.node.computed) {
        const k = prop.node.key.name || prop.node.key.value
        if (!DISPLAY_PROPS.has(k)) return
        const r = literal(path); if (!r) return
        if (inFunction(path)) edits.push([path.node.start, path.node.end, r])
        else edits.push([prop.node.start, prop.node.end, `get ${k}() { return ${r} }`])
      }
    },
  })

  if (!edits.length) return { file, count: 0, skipped, keys }
  // Nested ranges (a literal inside a property already rewritten) keep the outer edit.
  edits.sort((a, b) => a[0] - b[0] || b[1] - a[1])
  const flat = []
  for (const e of edits) {
    const last = flat[flat.length - 1]
    if (last && e[0] < last[1]) continue
    flat.push(e)
  }
  let out = src
  for (const [s, e, r] of flat.reverse()) out = out.slice(0, s) + r + out.slice(e)

  if (!/import\s*\{[^}]*\btr\b[^}]*\}\s*from\s*['"][^'"]*lib\/tr['"]/.test(out)) {
    let rel = relative(dirname(file), resolve(SRC, 'lib/tr')).replace(/\\/g, '/')
    if (!rel.startsWith('.')) rel = './' + rel
    const lastImport = [...out.matchAll(/^import[^\n]*(?:\n(?![\n])[^\n]*)*?from\s+['"][^'"]+['"];?\s*$/gm)].pop()
    const at = lastImport ? lastImport.index + lastImport[0].length : 0
    out = at ? out.slice(0, at) + `\nimport { tr } from '${rel}'` + out.slice(at)
      : `import { tr } from '${rel}'\n\n` + out
  }
  if (usesTrans && !/import\s*\{[^}]*\bTrans\b[^}]*\}\s*from\s*['"]react-i18next['"]/.test(out)) {
    if (/import\s*\{([^}]*)\}\s*from\s*['"]react-i18next['"]/.test(out))
      out = out.replace(/import\s*\{([^}]*)\}\s*from\s*(['"])react-i18next\2/, (m, names, q) => `import {${names.replace(/\s*$/, '')}, Trans } from ${q}react-i18next${q}`)
    else out = out.replace(/(import \{ tr \} from '[^']+')/, "$1\nimport { Trans } from 'react-i18next'")
  }
  if (!dry) writeFileSync(file, out)
  return { file, count: flat.length, skipped, keys }
}

if (process.argv[1] && process.argv[1].endsWith('i18n-wrap.mjs')) {
  const dry = process.argv.includes('--dry')
  const files = process.argv.slice(2).filter((a) => !a.startsWith('--'))
  let total = 0
  for (const f of files) {
    const r = wrapFile(resolve(f), { dry })
    total += r.count
    console.log(`${String(r.count).padStart(4)}  ${f}${r.skipped.length ? `  (${r.skipped.length} left)` : ''}`)
    if (process.argv.includes('--verbose')) r.skipped.forEach((s) => console.log('        ' + s))
  }
  console.log(`${total} strings wrapped`)
}
