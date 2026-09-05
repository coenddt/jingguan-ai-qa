/** 澄清表单卡：条件不足时提示用户补全单选/多选/输入，提交后拼成完整自然语言问题重问 */

import { useMemo, useState } from 'react'
import type { ClarifyForm as ClarifyFormData } from '../../../types'
import { useAsk } from '../qaContext'
import { useSnackbar } from '../../../hooks/useSnackbar'

interface Props {
  /** 澄清表单数据（text 引导文案 + question 原问题 + fields 字段列表） */
  form: ClarifyFormData
  /** 取消：收起表单（本卡无持久化，取消仅触发父级开关） */
  onCancel?: () => void
}

export default function ClarifyForm({ form, onCancel }: Props) {
  const ask = useAsk()
  const { showSnackbar } = useSnackbar()
  const [selected, setSelected] = useState<Record<string, string[]>>(() =>
    Object.fromEntries(form.fields.map((f) => [f.key, []])))
  const [inputs, setInputs] = useState<Record<string, string>>({})

  const yearField = useMemo(() => form.fields.find((f) => f.key === 'year'), [form.fields])

  const toggleChoice = (key: string, value: string) => {
    setSelected((prev) => {
      const cur = prev[key] ?? []
      // 多选 checkbox/select multiple
      const next = cur.includes(value) ? cur.filter((v) => v !== value) : [...cur, value]
      return { ...prev, [key]: next }
    })
  }

  const pickSingle = (key: string, value: string) => {
    // 单选 radio：恒选中当前值（同值再点即为保留该值）
    setSelected((prev) => ({ ...prev, [key]: [value] }))
  }

  const joinChoices = (vals: string[]) => vals.join('、')

  /** 回填拼词：year→句首年份前缀；多选 checkbox/select→"{label}为{v1}、{v2}"；input→"{label}为{value}" */
  const buildFullQuestion = (): string => {
    const yearVal = yearField ? (selected[yearField.key]?.[0] ?? '') : ''
    const parts: string[] = []
    for (const f of form.fields) {
      if (f.key === 'year') continue
      if (f.type === 'input') {
        const v = (inputs[f.key] ?? '').trim()
        if (v) parts.push(`${f.label}为${v}`)
        continue
      }
      const vals = (selected[f.key] ?? []).filter((v) => v)
      if (vals.length) parts.push(`${f.label}为${joinChoices(vals)}`)
    }
    const yearPrefix = yearVal ? `${yearVal}年` : ''
    const tail = parts.length ? `，${parts.join('，')}` : ''
    return `${yearPrefix}${form.question}${tail}`
  }

  const hasAny = (): boolean => {
    for (const f of form.fields) {
      if (f.type === 'input') {
        if ((inputs[f.key] ?? '').trim()) return true
      } else if ((selected[f.key] ?? []).some((v) => v)) {
        return true
      }
    }
    return false
  }

  const submit = () => {
    if (!hasAny()) {
      showSnackbar('请至少补充一项查询条件', 'warning')
      return
    }
    ask(buildFullQuestion())
  }

  return (
    <div className="clarify-form">
      <div className="dot-li mb-2">{form.text}</div>
      {form.fields.map((f) => (
        <div key={f.key} className="cf-field mb-3">
          <div className="cf-label mb-1 text-sm font-medium">
            {f.label}{f.required ? <span className="text-red-500"> *</span> : null}
          </div>
          {f.type === 'input' ? (
            <input
              className="input input-bordered input-sm w-full max-w-xs"
              placeholder={f.placeholder ?? `请输入${f.label}`}
              value={inputs[f.key] ?? ''}
              onChange={(e) => setInputs((p) => ({ ...p, [f.key]: e.target.value }))}
            />
          ) : f.type === 'radio' ? (
            <div className="flex flex-wrap gap-x-4 gap-y-1">
              {(f.options ?? []).map((opt) => (
                <label key={String(opt)} className="flex items-center gap-1 cursor-pointer">
                  <input
                    type="radio"
                    className="radio radio-primary radio-sm"
                    name={`cf-${f.key}`}
                    checked={(selected[f.key] ?? []).includes(String(opt))}
                    onChange={() => pickSingle(f.key, String(opt))}
                  />
                  <span className="text-sm">{opt}</span>
                </label>
              ))}
            </div>
          ) : f.type === 'select' ? (
            <select
              multiple
              size={Math.min((f.options ?? []).length, 6)}
              className="select select-bordered select-sm w-full max-w-xs"
              value={selected[f.key] ?? []}
              onChange={(e) =>
                setSelected((p) => ({
                  ...p,
                  [f.key]: Array.from(e.target.selectedOptions).map((o) => o.value),
                }))
              }
            >
              {(f.options ?? []).map((opt) => (
                <option key={String(opt)} value={String(opt)}>{opt}</option>
              ))}
            </select>
          ) : (
            <div className="flex flex-wrap gap-x-4 gap-y-1">
              {(f.options ?? []).map((opt) => (
                <label key={String(opt)} className="flex items-center gap-1 cursor-pointer">
                  <input
                    type="checkbox"
                    className="checkbox checkbox-primary checkbox-sm"
                    checked={(selected[f.key] ?? []).includes(String(opt))}
                    onChange={() => toggleChoice(f.key, String(opt))}
                  />
                  <span className="text-sm">{opt}</span>
                </label>
              ))}
            </div>
          )}
        </div>
      ))}
      <div className="flex gap-2 mt-2">
        <button className="btn btn-sm btn-primary" onClick={submit}>提交</button>
        {onCancel && <button className="btn btn-sm btn-ghost" onClick={onCancel}>取消</button>}
      </div>
    </div>
  )
}