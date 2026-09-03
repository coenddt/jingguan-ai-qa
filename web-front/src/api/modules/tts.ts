import { http } from '../client'

export const ttsApi = {
  synthesize: (text: string) => http.post<Blob>('/tts', { text }, { responseType: 'blob', timeout: 20000 }),
}
