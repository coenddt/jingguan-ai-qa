/** TTS 域纯业务函数（useTts 使用） */

import { ttsApi } from '../api/modules/tts'

/** 语音合成并创建可播放的 Audio 元素（播放/暂停状态由调用方管理） */
export async function synthesizeAudio(text: string): Promise<HTMLAudioElement> {
  const { data } = await ttsApi.synthesize(text)
  const url = URL.createObjectURL(data)
  return new Audio(url)
}
