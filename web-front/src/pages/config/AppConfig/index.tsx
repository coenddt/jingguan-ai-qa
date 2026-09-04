/** 应用配置页（原型 page-sys-app 1:1）：面包屑 + 6 张配置卡片（图标/开关/齿轮入口） + 开场白/常问设置弹窗 */

import { useCallback, useEffect, useState, type ChangeEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import Breadcrumb from '../../../components/Breadcrumb'
import Modal from '../../../components/Modal'
import { useConfigStore } from '../../../store/useConfigStore'
import { useGreetingForm } from '../../../hooks/useGreetingForm'
import { useSnackbar } from '../../../hooks/useSnackbar'
import type { AppConfig as AppConfigData } from '../../../types'
import type { SaveConfigFn } from '../../../hooks/useGreetingForm'

interface CardDef {
  key: 'greeting' | 'suggestions' | 'tts' | 'stt' | 'modelConfig' | 'hot'
  icon: string
  iconBg: string
  iconColor: string
  name: string
  desc: string
  gear?: { title: string; action: 'greeting' | 'model' | 'hot' }
}

const CARDS: CardDef[] = [
  {
    key: 'greeting', icon: 'fa-comments', iconBg: '#E8F0FE', iconColor: '#2563EB',
    name: '对话开场白', desc: '开启后，新对话将自动显示开场白引导语（如"欢迎使用智能AI问数..."）',
    gear: { title: '配置开场白', action: 'greeting' },
  },
  {
    key: 'suggestions', icon: 'fa-list', iconBg: '#FEF3C7', iconColor: '#D97706',
    name: '下一步问题建议', desc: '开启后，AI回复下方自动生成3条相关延伸问题提示条',
  },
  {
    key: 'tts', icon: 'fa-volume-up', iconBg: '#F0FDF4', iconColor: '#16A34A',
    name: '文字转语音', desc: '开启后，AI回答支持语音播报功能',
  },
  {
    key: 'stt', icon: 'fa-microphone', iconBg: '#F3E8FF', iconColor: '#9333EA',
    name: '语音转文字', desc: '开启后，支持通过语音输入问题',
  },
  {
    key: 'modelConfig', icon: 'fa-cube', iconBg: '#E8F0FE', iconColor: '#2563EB',
    name: '模型配置', desc: '配置各业务场景使用的AI模型',
    gear: { title: '配置模型', action: 'model' },
  },
  {
    key: 'hot', icon: 'fa-fire', iconBg: '#FEF3C7', iconColor: '#D97706',
    name: '常问设置', desc: '根据经常提问频次，在快捷提问中能看到常问问题',
    gear: { title: '配置常问设置', action: 'hot' },
  },
]

export default function AppConfig() {
  const fetchMethod = useConfigStore((s) => s.fetchMethod)
  const saveMethod = useConfigStore((s) => s.saveMethod)
  const config = useConfigStore((s) => s.config)
  const navigate = useNavigate()
  const { showSnackbar } = useSnackbar()

  const [greetingOpen, setGreetingOpen] = useState(false)
  const [hotOpen, setHotOpen] = useState(false)

  useEffect(() => {
    fetchMethod().catch(() => showSnackbar('配置加载失败', 'error'))
  }, [fetchMethod, showSnackbar])

  const save: SaveConfigFn = useCallback((patch, okMsg = '配置已保存，即时生效') => {
    saveMethod(patch)
      .then(() => showSnackbar(okMsg, 'success'))
      .catch(() => showSnackbar('保存失败，请重试', 'error'))
  }, [saveMethod, showSnackbar])

  const toggleCard = useCallback((key: CardDef['key'], checked: boolean) => {
    if (key === 'greeting') save({ greeting: { ...config.greeting, enabled: checked } })
    else if (key === 'hot') save({ hotRecommend: { ...config.hotRecommend, enabled: checked } })
    else save({ [key]: checked } as Partial<AppConfigData>)
  }, [config.greeting, config.hotRecommend, save])

  const onGear = useCallback((action: 'greeting' | 'model' | 'hot') => {
    if (action === 'greeting') setGreetingOpen(true)
    else if (action === 'hot') setHotOpen(true)
    else navigate('/config/model')
  }, [navigate])

  const checkedMap: Record<CardDef['key'], boolean> = {
    greeting: config.greeting.enabled !== false,
    suggestions: config.suggestions,
    tts: config.tts,
    stt: config.stt,
    modelConfig: config.modelConfig,
    hot: config.hotRecommend.enabled !== false,
  }

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <Breadcrumb />
      <div className="pg-card">
        <div className="app-config-grid">
          {CARDS.map((c) => (
            <div key={c.key} className="app-card">
              <div className="app-card-top">
                <div className="app-card-icon" style={{ background: c.iconBg, color: c.iconColor }}>
                  <i className={`fas ${c.icon}`} />
                </div>
                <span className="app-card-name">{c.name}</span>
                <div className="app-card-actions">
                  {c.gear && (
                    <button className="app-card-set" title={c.gear.title} onClick={() => onGear(c.gear!.action)}>
                      <i className="fas fa-cog" />
                    </button>
                  )}
                  <button type="button" className={`app-toggle ${checkedMap[c.key] ? 'on' : ''}`}
                    onClick={() => toggleCard(c.key, !checkedMap[c.key])} />
                </div>
              </div>
              <div className="app-card-desc">{c.desc}</div>
            </div>
          ))}
        </div>
      </div>

      <GreetingModal open={greetingOpen} onClose={() => setGreetingOpen(false)} save={save} />
      <HotModal open={hotOpen} onClose={() => setHotOpen(false)} save={save} />
    </div>
  )
}

/** 对话开场白弹窗（原型 greetingConfigModal 1:1） */
function GreetingModal({ open, onClose, save }: { open: boolean; onClose: () => void; save: SaveConfigFn }) {
  const {
    greetingText, changeGreetingText,
    questions, newQ, changeNewQ, addQuestion, removeQuestion, canAddQuestion, saveGreeting,
  } = useGreetingForm(save)

  const submit = useCallback(() => {
    if (!greetingText.trim()) {
      return
    }
    saveGreeting()
    onClose()
  }, [greetingText, saveGreeting, onClose])

  return (
    <Modal open={open} onClose={onClose} boxClassName="max-w-[560px]" showClose
      title={<h3 className="font-bold text-lg flex items-center"><i className="fas fa-comments mr-1.5" style={{ color: 'var(--primary)' }} />对话开场白</h3>}
      footerClassName="justify-between"
      footer={<>
        <button className="btn btn-text whitespace-nowrap" onClick={onClose}><i className="fas fa-times" /> 取消</button>
        <button className="btn btn-primary whitespace-nowrap" disabled={!greetingText.trim()} onClick={submit}>
          <i className="fas fa-check" /> 保存
        </button>
      </>}>
      <div style={{ marginBottom: 16 }}>
        <label style={{ display: 'block', fontSize: 15, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 6 }}>开场白文案</label>
        <textarea value={greetingText} onChange={(e) => changeGreetingText(e.target.value)} placeholder="请输入欢迎开场白…"
          style={{ width: '100%', height: 80, padding: 10, border: '1px solid var(--border)', borderRadius: 6, fontSize: 15, resize: 'vertical', outline: 'none', boxSizing: 'border-box', background: 'var(--bg-muted)', color: 'var(--text-body)', fontFamily: 'inherit' }} />
      </div>
      <div>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
          <label style={{ fontSize: 15, fontWeight: 600, color: 'var(--text-primary)' }}>开场问题 · {questions.length}/10</label>
          <button className="btn btn-text btn-sm whitespace-nowrap gap-1" onClick={addQuestion} disabled={!canAddQuestion}>
            <i className="fas fa-plus" /> 添加开场问题
          </button>
        </div>
        {questions.map((q, i) => (
          <div key={`${q}-${i}`} className="gq-row">
            <input className="gq-input" value={q} readOnly placeholder="请输入快捷问题" maxLength={100} />
            <button className="gq-del" onClick={() => removeQuestion(i)}><i className="fas fa-times" /></button>
          </div>
        ))}
        {canAddQuestion && (
          <div className="gq-row">
            <input className="gq-input" value={newQ} onChange={(e) => changeNewQ(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && addQuestion()} placeholder="请输入快捷问题" maxLength={100} />
            <button className="gq-del" style={{ visibility: 'hidden' }}><i className="fas fa-times" /></button>
          </div>
        )}
      </div>
    </Modal>
  )
}

/** 常问设置弹窗（原型 hotConfigModal 1:1） */
function HotModal({ open, onClose, save }: { open: boolean; onClose: () => void; save: SaveConfigFn }) {
  const hotRecommend = useConfigStore((s) => s.config.hotRecommend)
  const [threshold, setThreshold] = useState(hotRecommend.threshold)

  useEffect(() => {
    if (open) setThreshold(hotRecommend.threshold)
  }, [open, hotRecommend])

  const changeThreshold = useCallback((e: ChangeEvent<HTMLInputElement>) => {
    setThreshold(Math.max(1, Number(e.target.value) || 1))
  }, [])

  const submit = useCallback(() => {
    save({ hotRecommend: { ...hotRecommend, threshold } })
    onClose()
  }, [hotRecommend, threshold, save, onClose])

  return (
    <Modal open={open} onClose={onClose} boxClassName="max-w-[480px]" showClose
      title={<h3 className="font-bold text-lg flex items-center"><i className="fas fa-fire mr-1.5" />常问设置</h3>}
      footer={<>
        <button className="btn btn-text whitespace-nowrap" onClick={onClose}>取消</button>
        <button className="btn btn-primary whitespace-nowrap" onClick={submit}>保存</button>
      </>}>
      <div style={{ marginBottom: 12 }}>
        <label style={{ display: 'block', fontSize: 15, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 4 }}>问题频次阈值</label>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <input type="number" min={1} value={threshold} onChange={changeThreshold}
            style={{ width: 100, height: 36, padding: '0 10px', border: '1px solid var(--border)', borderRadius: 6, fontSize: 15, outline: 'none', background: 'var(--bg-muted)', color: 'var(--text-body)', boxSizing: 'border-box' }} />
          <span style={{ fontSize: 14, color: 'var(--text-hint)' }}>次（同一问题出现次数超过此值即视为常问）</span>
        </div>
      </div>
    </Modal>
  )
}
