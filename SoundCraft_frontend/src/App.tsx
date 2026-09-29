import { useState } from 'react'
import { ToolBar } from './components/mainPage/Toolbar'
import { ChatSection } from './components/chatComponents/ChatSection'
import { AudioView } from './components/audioComponents/AudioView'
import { downloadResultAudio, uploadAudio, uploadPrompt, waitForResult } from './api/soundcraft'
import './app.css'
import './fontStylesheet.css'

function App() {
  const [audioFile, setAudioFile] = useState<File | null>(null)
  const [agentResponse, setAgentResponse] = useState<Record<string, unknown> | null>(null)
  const [resultAudioFile, setResultAudioFile] = useState<File | null>(null)
  const [requestId, setRequestId] = useState<string | null>(null)
  const [isProcessing, setIsProcessing] = useState(false)

  const handleAudioUpload = async (file: File) => {
    try {
      const uploadResult = await uploadAudio(file)
      setAudioFile(file)
      setRequestId(uploadResult.request_id)
      setAgentResponse(null)
      setResultAudioFile(null)
    } catch (error) {
      console.error(error)
      alert('Audio upload failed.')
    }
  }

  const handlePromptSubmit = async (prompt: string): Promise<boolean> => {
    if (!requestId) {
      alert('Please upload an audio file first.')
      return false
    }

    try {
      setIsProcessing(true)
      setAgentResponse(null)
      setResultAudioFile(null)

      await uploadPrompt(requestId, prompt)
      // Rejestr backendu pamięta wcześniejszy callback, więc WebSocket można
      // otworzyć po poprawnym przyjęciu promptu bez ryzyka utraty zdarzenia.
      const completedResult = await waitForResult(requestId)

      setAgentResponse(completedResult.response)
      if (completedResult.response.execution_code === 'PASSED') {
        setResultAudioFile(await downloadResultAudio(requestId))
      }
      return true
    } catch (error) {
      console.error(error)
      alert('Something went wrong.')
      return false
    } finally {
      setIsProcessing(false)
    }
  }

  return (
    <>
      <ToolBar />
      <section id="center" aria-busy={isProcessing}>
        <ChatSection onPromptSubmit={handlePromptSubmit} agentResponse={agentResponse} />
        <AudioView
          onAudioSelected={handleAudioUpload}
          audioFile={audioFile}
          resultAudioFile={resultAudioFile}
        />
      </section>
    </>
  )
}

export default App
