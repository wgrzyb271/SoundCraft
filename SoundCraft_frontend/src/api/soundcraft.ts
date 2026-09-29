import type {
  CompletedResponse,
  ResultResponse,
  UploadAudioResponse,
  UploadPromptResponse,
} from './types'

const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

export async function uploadAudio(audioFile: File): Promise<UploadAudioResponse> {
  const formData = new FormData()
  formData.append('audio', audioFile)
  const response = await fetch(`${API_URL}/upload/audio/`, {
    method: 'POST',
    body: formData,
  })
  if (!response.ok) throw new Error(`Audio upload failed: ${response.status}`)
  return response.json()
}

export async function uploadPrompt(
  requestId: string,
  prompt: string,
): Promise<UploadPromptResponse> {
  const formData = new FormData()
  formData.append('prompt', prompt)
  const response = await fetch(`${API_URL}/upload/${encodeURIComponent(requestId)}/prompt`, {
    method: 'POST',
    body: formData,
  })
  if (!response.ok) throw new Error(`Prompt upload failed: ${response.status}`)
  return response.json()
}

export async function getResult(requestId: string): Promise<ResultResponse> {
  const response = await fetch(`${API_URL}/result/${encodeURIComponent(requestId)}/agent_response`)
  if (!response.ok) throw new Error(`Failed to get result: ${response.status}`)
  return response.json()
}

export async function waitForResult(
  requestId: string,
  timeoutMs = 5_400_000,
): Promise<CompletedResponse> {
  const websocketUrl = new URL(`/ws/result/${encodeURIComponent(requestId)}`, API_URL)
  websocketUrl.protocol = websocketUrl.protocol === 'https:' ? 'wss:' : 'ws:'

  try {
    await new Promise<void>((resolve, reject) => {
      const socket = new WebSocket(websocketUrl)
      let finished = false
      const finish = (callback: () => void) => {
        if (finished) return
        finished = true
        window.clearTimeout(timer)
        socket.close()
        callback()
      }
      const timer = window.setTimeout(
        () => finish(() => reject(new Error('Processing notification timed out'))),
        timeoutMs,
      )

      socket.onmessage = event => {
        const notice = JSON.parse(event.data) as { status?: string }
        if (notice.status === 'completed') finish(resolve)
        if (notice.status === 'timeout') {
          finish(() => reject(new Error('WCSS processing timed out')))
        }
      }
      socket.onerror = () => finish(() => reject(new Error('Completion WebSocket failed')))
      socket.onclose = () => {
        if (!finished) {
          finish(() => reject(new Error('Completion WebSocket closed unexpectedly')))
        }
      }
    })
  } catch (notificationError) {
    // Jedna próba odzyskania wyniku. Nie ma pętli pollingowej ani ponownych
    // połączeń do WCSS, więc awaria callbacku nie powoduje lawiny logowań SSH.
    const recovered = await getResult(requestId)
    if (recovered.status === 'completed') return recovered
    throw notificationError
  }

  const result = await getResult(requestId)
  if (result.status !== 'completed') {
    throw new Error('Backend was notified, but the result file is unavailable')
  }
  return result
}

export async function downloadResultAudio(requestId: string): Promise<File> {
  const response = await fetch(`${API_URL}/result/${encodeURIComponent(requestId)}/audio`)
  if (!response.ok) throw new Error(`Failed to download result audio: ${response.status}`)
  return new File([await response.blob()], 'result.wav', { type: 'audio/wav' })
}
