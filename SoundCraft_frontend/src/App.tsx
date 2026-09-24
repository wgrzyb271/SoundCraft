import { ToolBar } from './components/mainPage/Toolbar'
import { ChatSection } from './components/chatComponents/ChatSection'
import { AudioView } from './components/audioComponents/AudioView'
import './app.css'
import './fontStylesheet.css'
import { useState } from 'react'
import { uploadAudio, waitForResult, downloadResultAudio } from './api/soundcraft'
function App() {

  const [audioFile, setAudioFile] =useState<File | null>(null);
  const [agentResponse, setAgentResponse] =useState<Record<string, unknown> | null>(null);
  const [resultAudioFile, setResultAudioFile] = useState<File | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);

  const handlePromptSubmit = async (prompt: string) => {

      if (!audioFile) {
            alert("Please upload an audio file first.");
            return;
        }

      try {
          setIsProcessing(true);

          setAgentResponse(null);
          setResultAudioFile(null);

          const uploadResult = await uploadAudio(audioFile, prompt);
          const requestId = uploadResult.request_id;
          const completedResult = await waitForResult(requestId);

          setAgentResponse(completedResult.response);
          const resultFile = await downloadResultAudio(requestId);
          setResultAudioFile(resultFile);

        } 
        catch (error) {
            console.error(error);
            alert("Something went wrong.");
        } 
        finally {
            setIsProcessing(false);
        }};

  return (
    <>
    <ToolBar></ToolBar>
      <section id="center">
        <ChatSection onPromptSubmit={handlePromptSubmit} agentResponse={agentResponse}></ChatSection>
        <AudioView setAudioFile={setAudioFile} audioFile={audioFile} resultAudioFile={resultAudioFile}></AudioView>
      </section>
    </>
  )
}

export default App
