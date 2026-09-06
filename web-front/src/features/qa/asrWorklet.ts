/**
 * ASR 音频采集 AudioWorklet 处理器（替代已弃用的 ScriptProcessorNode）。
 *
 * worklet 运行在独立音频线程：
 * - process(inputs)：AudioContext(16k) 内部自动降采样后的 Float32 帧
 * - 钳位 [-1,1] → int16（与旧 ScriptProcessorNode.onaudioprocess 逻辑等价）
 * - 每帧经 node.port.postMessage(ArrayBuffer) 下行给主线程上传 WS
 *
 * 采用 Blob URL 内嵌：dev/build/E2E 跨环境同源可用，无需 Vite 特判打包 worklet 文件。
 */

export const ASR_PROCESSOR_NAME = 'asr-pcm-int16'

const SOURCE = `
class AsrPcmInt16Processor extends AudioWorkletProcessor {
  process(inputs) {
    const input = inputs[0]
    const ch = input && input[0]
    if (!ch || !ch.length) return true
    const i16 = new Int16Array(ch.length)
    for (let i = 0; i < ch.length; i++) {
      const v = Math.max(-1, Math.min(1, ch[i]))
      i16[i] = v < 0 ? v * 0x8000 : v * 0x7fff
    }
    this.port.postMessage(i16.buffer, [i16.buffer])
    return true
  }
}
registerProcessor(${JSON.stringify(ASR_PROCESSOR_NAME)}, AsrPcmInt16Processor)
`

let cachedUrl: string | null = null

/** 返回 worklet 模块 URL（首次创建后缓存复用，避免每次录音反复 createObjectURL）。 */
export function getAsrWorkletUrl(): string {
  if (!cachedUrl) {
    cachedUrl = URL.createObjectURL(new Blob([SOURCE], { type: 'application/javascript' }))
  }
  return cachedUrl
}