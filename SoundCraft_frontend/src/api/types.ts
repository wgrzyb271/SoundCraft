export interface UploadAudioResponse {
  status: 'received'
  request_id: string
  filename: string
}

export interface UploadPromptResponse {
  status: 'received'
  request_id: string
  prompt: string
}

export interface ProcessingResponse {
  status: 'processing' | 'expired'
  request_id: string
}

export interface CompletedResponse {
  status: 'completed'
  request_id: string
  response: {
    execution_code: 'PASSED' | 'FAILED'
    error_message?: string | null
    [key: string]: unknown
  }
}

export type ResultResponse = ProcessingResponse | CompletedResponse
