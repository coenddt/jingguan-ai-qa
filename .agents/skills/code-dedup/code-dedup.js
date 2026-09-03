/**
 * code-dedup.js — 代码去重检查与自动重构 CLI
 *
 * 检查指定目录或文件是否符合代码去重规范：
 *   规则1：同一逻辑在 2+ 处出现 → 提取为公共函数
 *   规则2：同一函数被 2+ 处引用 → 迁移到公共区
 *   规则3：3+ 同类公共函数 → 聚合到同一文件（无状态→utils，有状态→class）
 *
 * 用法：
 *   node code-dedup.js --bundle '{"cmd":"check","path":"server-finance/service"}'
 *   node code-dedup.js --bundle '{"cmd":"check","path":"miniapp-finance/utils","fix":true}'
 *   echo '{"cmd":"check","path":"server-finance/service"}' | node code-dedup.js --stdin
 *
 * 参数（JSON，--bundle 单引号内联 或 stdin）：
 *   cmd:   "check" | "refactor"  — 检查 / 检查并自动重构
 *   path:  目录或文件路径（相对于工作目录）
 *   fix:   boolean — 是否自动重构（默认 false，仅检查报告）
 *   exclude: string[] — 排除的 glob 模式（如 ["node_modules/**", "test/**"]）
 */

const fs = require('fs')
const path = require('path')

// ──────────────────────────────────────────────
// 配置
// ──────────────────────────────────────────────

const DEFAULT_EXCLUDE = [
  'node_modules/**',
  '.git/**',
  'tmp/**',
  'dist/**',
  'build/**',
  '*.min.js',
  '*.test.js',
  '*_test.js',
]

// 支持的源码扩展名
const SRC_EXTENSIONS = ['.js', '.ts', '.jsx', '.tsx']

// ──────────────────────────────────────────────
// AST 级轻量分析（正则 + 启发式，不引入 AST 依赖）
// ──────────────────────────────────────────────

/**
 * 提取文件中所有函数定义（function 声明 + 箭头函数赋值）
 * 返回 [{ name, start, end, body, params }]
 */
function extractFunctions(content, filePath) {
  const funcs = []

  // 1. function 声明: function name(args) { body }
  const funcDeclRe = /^function\s+(\w+)\s*\(([^)]*)\)\s*\{/gm
  let m
  while ((m = funcDeclRe.exec(content)) !== null) {
    const name = m[1]
    const params = m[2].split(',').map(s => s.trim()).filter(Boolean)
    const bodyStart = m.index + m[0].length
    const bodyEnd = findMatchingBrace(content, bodyStart)
    if (bodyEnd > bodyStart) {
      funcs.push({
        name,
        params,
        body: content.slice(bodyStart, bodyEnd),
        start: m.index,
        end: bodyEnd,
        filePath,
        kind: 'function',
        signature: `${name}(${params.join(', ')})`,
      })
    }
  }

  // 2. 箭头函数赋值: const name = (args) => { body } 或 const name = (args) => expr
  const arrowRe = /^(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?\(([^)]*)\)\s*=>\s*\{/gm
  while ((m = arrowRe.exec(content)) !== null) {
    const name = m[1]
    const params = m[2].split(',').map(s => s.trim()).filter(Boolean)
    const bodyStart = m.index + m[0].length
    const bodyEnd = findMatchingBrace(content, bodyStart)
    if (bodyEnd > bodyStart) {
      funcs.push({
        name,
        params,
        body: content.slice(bodyStart, bodyEnd),
        start: m.index,
        end: bodyEnd,
        filePath,
        kind: 'arrow',
        signature: `${name}(${params.join(', ')})`,
      })
    }
  }

  // 3. 模块导出函数: module.exports = { func, ... }
  //    已被上面两种覆盖，无需额外处理

  return funcs
}

/** 从给定位置找到匹配的 } */
function findMatchingBrace(content, start) {
  let depth = 1
  let i = start
  while (i < content.length && depth > 0) {
    if (content[i] === '{') depth++
    else if (content[i] === '}') depth--
    i++
  }
  return depth === 0 ? i : -1
}

/** 规范化函数体用于比较（去除空白和注释） */
function normalizeBody(body) {
  return body
    .replace(/\/\/.*$/gm, '')          // 行注释
    .replace(/\/\*[\s\S]*?\*\//g, '')   // 块注释
    .replace(/\s+/g, '')                // 所有空白
    .replace(/['"]/g, '"')              // 统一引号
}

/** 计算两个函数体的相似度（0~1） */
function similarity(a, b) {
  const na = normalizeBody(a)
  const nb = normalizeBody(b)
  if (na === nb) return 1.0
  if (na.length < 10 || nb.length < 10) return 0
  // 简单相似度：较短串在较长串中的占比
  const shorter = na.length <= nb.length ? na : nb
  const longer = na.length <= nb.length ? nb : na
  if (longer.indexOf(shorter) !== -1) return shorter.length / longer.length
  // 基于字符频率的近似比较
  const freqA = charFreq(na)
  const freqB = charFreq(nb)
  let dot = 0, magA = 0, magB = 0
  for (const k in freqA) {
    magA += freqA[k] * freqA[k]
    if (freqB[k]) dot += freqA[k] * freqB[k]
  }
  for (const k in freqB) magB += freqB[k] * freqB[k]
  if (magA === 0 || magB === 0) return 0
  return dot / (Math.sqrt(magA) * Math.sqrt(magB))
}

function charFreq(s) {
  const f = {}
  for (let i = 0; i < s.length; i++) {
    const c = s[i]
    f[c] = (f[c] || 0) + 1
  }
  return f
}

// ──────────────────────────────────────────────
// 文件收集
// ──────────────────────────────────────────────

function collectFiles(dirPath, excludePatterns) {
  const result = []
  if (!fs.existsSync(dirPath)) return result

  const stat = fs.statSync(dirPath)
  if (stat.isFile()) {
    if (SRC_EXTENSIONS.includes(path.extname(dirPath))) {
      result.push(dirPath)
    }
    return result
  }

  if (!stat.isDirectory()) return result

  const entries = fs.readdirSync(dirPath)
  for (const entry of entries) {
    const full = path.join(dirPath, entry)
    if (isExcluded(full, excludePatterns)) continue
    result.push(...collectFiles(full, excludePatterns))
  }
  return result
}

function isExcluded(filePath, patterns) {
  const rel = filePath.replace(/\\/g, '/')
  for (const p of patterns) {
    const glob = p.replace(/\*\*/g, '(.+)').replace(/\*/g, '[^/]*').replace(/\?/g, '.')
    const re = new RegExp(glob)
    if (re.test(rel)) return true
  }
  return false
}

// ──────────────────────────────────────────────
// 规则检测
// ──────────────────────────────────────────────

/** 函数名是否"语义相同"（规则1判定前提）：
 *  - 完全同名：normalizeConclusionMarkdown vs normalizeConclusionMarkdown
 *  - 前缀下划线差异：_normalizeConclusionMarkdown vs normalizeConclusionMarkdown
 *  - 首字母大小写差异：normalizeConclusionMarkdown vs NormalizeConclusionMarkdown
 *  - 前缀动词差异（同一逻辑不同命名习惯）：normalize vs _normalize
 *  注意：名称完全不同（如 stripInline vs normalizeConclusionMarkdown）即使实现相似
 *  也视为不同职责，不判为重复逻辑，避免误报。
 */
function namesMatch(a, b) {
  const na = a.replace(/^_+/, '').toLowerCase()
  const nb = b.replace(/^_+/, '').toLowerCase()
  if (na === nb) return true
  // 一方是另一方的完整子串（如 normalize vs normalizeConclusionMarkdown 不算，
  // 但 getNormalizeX vs normalizeX 视为同族）——仅允许前缀差异
  const shorter = na.length <= nb.length ? na : nb
  const longer = na.length <= nb.length ? nb : na
  return longer.startsWith(shorter) && shorter.length >= 4
}

/** 规则1：检测重复逻辑（函数名匹配 + 相似度 > 0.9） */
function detectDuplicateLogic(files) {
  const allFuncs = []
  for (const f of files) {
    const content = fs.readFileSync(f, 'utf8')
    const funcs = extractFunctions(content, f)
    allFuncs.push(...funcs)
  }

  const duplicates = []
  const compared = new Set()

  for (let i = 0; i < allFuncs.length; i++) {
    for (let j = i + 1; j < allFuncs.length; j++) {
      const a = allFuncs[i]
      const b = allFuncs[j]
      // 同一文件内的函数不视为重复（可能是互相依赖的）
      if (a.filePath === b.filePath) continue
      // ★ 规则1 前提：函数名必须语义相同，避免不同职责的相似实现被误报
      if (!namesMatch(a.name, b.name)) continue
      const sim = similarity(a.body, b.body)
      if (sim > 0.9) {
        const key = [a.signature, b.signature].sort().join('|')
        if (!compared.has(key)) {
          compared.add(key)
          duplicates.push({
            rule: 1,
            type: 'duplicate_logic',
            files: [a.filePath, b.filePath],
            functions: [a.signature, b.signature],
            similarity: Math.round(sim * 100),
            message: `函数 "${a.signature}" 和 "${b.signature}" 相似度 ${Math.round(sim * 100)}%，可提取为公共函数`,
            suggestion: extractSuggestion(a, b),
          })
        }
      }
    }
  }

  return { allFuncs, duplicates }
}

/** 规则2：检测跨文件重复函数（同名+相似实现） */
function detectCrossFileDuplicates(allFuncs) {
  const byName = {}
  for (const f of allFuncs) {
    if (!byName[f.name]) byName[f.name] = []
    byName[f.name].push(f)
  }

  const issues = []
  for (const [name, funcs] of Object.entries(byName)) {
    if (funcs.length < 2) continue
    const files = [...new Set(funcs.map(f => f.filePath))]
    if (files.length < 2) continue  // 同一文件内不视为问题

    // 计算两两相似度
    for (let i = 0; i < funcs.length; i++) {
      for (let j = i + 1; j < funcs.length; j++) {
        if (funcs[i].filePath === funcs[j].filePath) continue
        const sim = similarity(funcs[i].body, funcs[j].body)
        if (sim > 0.85) {
          issues.push({
            rule: 2,
            type: 'cross_file_duplicate',
            files: [funcs[i].filePath, funcs[j].filePath],
            functions: [funcs[i].signature, funcs[j].signature],
            similarity: Math.round(sim * 100),
            message: `函数 "${name}" 在 ${files.length} 个文件中重复定义，相似度 ${Math.round(sim * 100)}%，应迁移到公共区`,
            suggestion: `将 "${name}" 提取到 ${suggestSharedLocation(funcs[i], funcs[j])}`,
          })
        }
      }
    }
  }

  return issues
}

/** 规则3：检测同类公共函数聚合（>3 个相似函数应聚合） */
function detectMissingAggregation(allFuncs, basePath) {
  // 按前缀/功能分组，检测同文件中是否有 >3 个同类函数
  // 简化实现：查找 utils 文件中函数命名模式
  const utilsFiles = allFuncs.filter(f => {
    const rel = path.relative(basePath, f.filePath).replace(/\\/g, '/')
    return rel.includes('utils') || rel.includes('common') || rel.includes('shared')
  })

  const issues = []
  const byFile = {}
  for (const f of utilsFiles) {
    if (!byFile[f.filePath]) byFile[f.filePath] = []
    byFile[f.filePath].push(f)
  }

  // 检查非 utils 文件中的公共函数是否分散
  const nonUtilsFuncs = allFuncs.filter(f => {
    const rel = path.relative(basePath, f.filePath).replace(/\\/g, '/')
    return !rel.includes('utils') && !rel.includes('common') && !rel.includes('shared')
  })

  // 按功能前缀分组（normalize, format, parse, render, build 等）
  const prefixGroups = {}
  for (const f of nonUtilsFuncs) {
    const prefix = f.name.match(/^(normalize|format|parse|render|build|convert|transform|compute|generate)[A-Z]/)
    if (!prefix) continue
    const key = prefix[1]
    if (!prefixGroups[key]) prefixGroups[key] = []
    prefixGroups[key].push(f)
  }

  for (const [prefix, funcs] of Object.entries(prefixGroups)) {
    if (funcs.length >= 3) {
      const files = [...new Set(funcs.map(f => f.filePath))]
      if (files.length >= 2) {
        issues.push({
          rule: 3,
          type: 'missing_aggregation',
          files,
          functions: funcs.map(f => f.signature),
          message: `发现 ${funcs.length} 个 "${prefix}*" 前缀的分散函数（分布在 ${files.length} 个文件），建议聚合到统一的 ${prefix}-utils.js`,
          suggestion: `创建 ${prefix}-utils.js 聚合这些函数`,
        })
      }
    }
  }

  return issues
}

// ──────────────────────────────────────────────
// 建议生成
// ──────────────────────────────────────────────

function extractSuggestion(a, b) {
  const dirA = path.dirname(a.filePath)
  const dirB = path.dirname(b.filePath)
  const commonDir = findCommonDir(dirA, dirB)
  const funcName = a.name
  return `将 ${funcName} 提取到 ${commonDir}/shared-utils.js 或相邻的公共工具文件`
}

function findCommonDir(dirA, dirB) {
  const partsA = dirA.split(path.sep)
  const partsB = dirB.split(path.sep)
  const common = []
  for (let i = 0; i < Math.min(partsA.length, partsB.length); i++) {
    if (partsA[i] === partsB[i]) common.push(partsA[i])
    else break
  }
  return common.join(path.sep) || '.'
}

function suggestSharedLocation(a, b) {
  const commonDir = findCommonDir(path.dirname(a.filePath), path.dirname(b.filePath))
  const relA = path.relative(commonDir, a.filePath).replace(/\\/g, '/')
  // 查找最近的 utils 文件
  const utilsFile = findNearestUtils(commonDir)
  if (utilsFile) return utilsFile
  return `${commonDir}/markdown-utils.js`
}

function findNearestUtils(fromDir) {
  let dir = fromDir
  const maxDepth = 5
  for (let d = 0; d < maxDepth; d++) {
    const candidate = path.join(dir, 'markdown-utils.js')
    if (fs.existsSync(candidate)) return candidate
    const candidate2 = path.join(dir, 'utils.js')
    if (fs.existsSync(candidate2)) return candidate2
    const candidate3 = path.join(dir, 'common.js')
    if (fs.existsSync(candidate3)) return candidate3
    const parent = path.dirname(dir)
    if (parent === dir) break
    dir = parent
  }
  return null
}

// ──────────────────────────────────────────────
// 主流程
// ──────────────────────────────────────────────

function runCheck(input) {
  const { cmd = 'check', path: targetPath, fix = false, exclude = [] } = input
  const absPath = path.resolve(targetPath)

  if (!fs.existsSync(absPath)) {
    return { error: `路径不存在: ${targetPath}` }
  }

  const excludePatterns = [...DEFAULT_EXCLUDE, ...exclude]
  const files = collectFiles(absPath, excludePatterns)

  if (files.length === 0) {
    return { summary: '未找到源码文件', fileCount: 0 }
  }

  const { allFuncs, duplicates } = detectDuplicateLogic(files)
  const crossFileIssues = detectCrossFileDuplicates(allFuncs)
  const aggregationIssues = detectMissingAggregation(allFuncs, absPath)

  const allIssues = [...duplicates, ...crossFileIssues, ...aggregationIssues]

  const summary = {
    rule1_duplicate_logic: duplicates.length,
    rule2_cross_file: crossFileIssues.length,
    rule3_aggregation: aggregationIssues.length,
    totalIssues: allIssues.length,
    fileCount: files.length,
    functionCount: allFuncs.length,
  }

  return {
    summary,
    issues: allIssues,
    fix: fix ? applyFixes(allIssues, absPath) : null,
  }
}

function applyFixes(issues, basePath) {
  const fixes = []
  for (const issue of issues) {
    // 安全化修复：只生成建议，不自动修改（防止误改）
    fixes.push({
      issueId: `${issue.rule}-${issue.type}`,
      message: issue.message,
      suggestion: issue.suggestion,
      autoFixable: false,  // 自动重构风险高，仅生成建议
      steps: generateFixSteps(issue, basePath),
    })
  }
  return fixes
}

function generateFixSteps(issue, basePath) {
  const steps = []
  const files = issue.files || []
  const funcs = issue.functions || []

  if (issue.rule === 1) {
    steps.push(`1. 读取 ${files[0]} 和 ${files[1]} 中 ${funcs[0]} / ${funcs[1]} 的函数体`)
    steps.push(`2. 统一实现，选择参数最完整的版本作为基准`)
    steps.push(`3. 在公共区创建新文件或添加到已有 utils 文件`)
    steps.push(`4. 修改 ${files[0]} 和 ${files[1]}，引入公共函数替代本地定义`)
  } else if (issue.rule === 2) {
    steps.push(`1. 读取 ${files.join(', ')} 中同名函数的实现`)
    steps.push(`2. 合并为单一实现，放到公共区（如 markdown-utils.js）`)
    steps.push(`3. 所有原文件改为 require/import 公共函数`)
  } else if (issue.rule === 3) {
    steps.push(`1. 创建聚合文件（如 ${issue.functions[0].split('(')[0].replace(/format|normalize|parse/, '')}-utils.js）`)
    steps.push(`2. 将分散的函数迁移到新文件`)
    steps.push(`3. 各原文件改为 require/import 新文件`)
  }

  return steps
}

// ──────────────────────────────────────────────
// CLI 入口
// ──────────────────────────────────────────────

async function main() {
  const args = process.argv.slice(2)
  const stdinMode = args.includes('--stdin')
  const bIdx = args.indexOf('--bundle')

  let input
  if (bIdx >= 0 && args[bIdx + 1]) {
    try {
      input = JSON.parse(args[bIdx + 1])
    } catch (e) {
      console.error('--bundle JSON 解析失败:', e.message)
      process.exit(1)
    }
  } else if (stdinMode) {
    try {
      const raw = fs.readFileSync(0, 'utf8')
      input = JSON.parse(raw.trim())
    } catch (e) {
      console.error('stdin JSON 解析失败:', e.message)
      process.exit(1)
    }
  } else {
    // 兼容直接传参
    const posArg = args.find(a => !a.startsWith('--'))
    input = { cmd: 'check', path: posArg || '.' }
  }

  const result = runCheck(input)

  // 格式化输出
  if (result.error) {
    console.error(JSON.stringify(result, null, 2))
    process.exit(1)
  }

  console.log(JSON.stringify(result, null, 2))

  if (result.summary && result.summary.totalIssues > 0) {
    process.exit(0)  // 有问题也正常退出，由调用方决定
  }
}

main().catch(err => {
  console.error('执行失败:', err.message)
  process.exit(1)
})
