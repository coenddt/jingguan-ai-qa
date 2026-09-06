/** TTS 域纯业务函数（useTts 使用） */

import { ttsApi } from '../api/modules/tts'

/** 语音合成并创建可播放的 Audio 元素（播放/暂停状态由调用方管理）；signal 用于中止加载 */
export async function synthesizeAudio(text: string, signal?: AbortSignal): Promise<HTMLAudioElement> {
  const { data } = await ttsApi.synthesize(text, signal)
  const url = URL.createObjectURL(data)
  const audio = new Audio(url)
  // 播放结束即释放 blob URL（addEventListener 不与调用方 onended 赋值互相覆盖）
  audio.addEventListener('ended', () => URL.revokeObjectURL(url))
  return audio
}
