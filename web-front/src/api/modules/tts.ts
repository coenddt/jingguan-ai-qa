import { http } from '../client'

export const ttsApi = {
  synthesize: (text: string, signal?: AbortSignal) =>
    http.post<Blob>('/tts', { text }, { responseType: 'blob', timeout: 20000, signal }),
}
