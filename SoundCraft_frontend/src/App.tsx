import { ToolBar } from './components/mainPage/Toolbar'
import { ChatSection } from './components/chatComponents/ChatSection'
import { AudioView } from './components/audioComponents/AudioView'
import './app.css'
import './fontStylesheet.css'
import { useState } from 'react'
import { uploadAudio, connectToResult, downloadResultAudio, uploadPrompt, getAgentResponse } from './api/soundcraft'
function App() {

  const [audioFile, setAudioFile] =useState<File | null>(null);
  const [agentResponse, setAgentResponse] =useState<Record<string, unknown> | null>(null);
  const [resultAudioFile, setResultAudioFile] = useState<File | null>(null);
   const [request_id, setRequestId] = useState<string|null>(null);
  const [isProcessing, setIsProcessing] = useState(false);

  const handleAudioUpload = async (file:File)=>{
    try{
      setAudioFile(file);
      console.log("DEBUG HANDLE AUDIO UPLOAD")
      const uploadResult = await uploadAudio(file);
      console.log("REQUEST ID: ", uploadResult.request_id)
      setRequestId(uploadResult.request_id)
    }
    catch(error){
      console.error(error);
      alert("Audio upload failed.")
    }
  }
  const handlePromptSubmit = async (prompt: string): Promise<Boolean>=>{

      if (!request_id) {
            alert("Please upload an audio file first.");
            return false;
        }

      try {
          setIsProcessing(true);
          setAgentResponse(null);
          setResultAudioFile(null);

          const resultPromise = connectToResult(request_id);

          await uploadPrompt(request_id, prompt);
          await resultPromise;

          const result = await getAgentResponse(request_id);
          setAgentResponse(result);

          const resultFile = await downloadResultAudio(request_id);
          setResultAudioFile(resultFile);
          return true;
        } 
      catch (error) {
            console.error(error);
            alert("Something went wrong.");
            return false;
        } 
        finally {
            setIsProcessing(false);
        }};

  return (
    <>
    <ToolBar></ToolBar>
      <section id="center">
        <ChatSection onPromptSubmit={handlePromptSubmit} agentResponse={agentResponse}></ChatSection>
        <AudioView onAudioSelected={handleAudioUpload} audioFile={audioFile} resultAudioFile={resultAudioFile}></AudioView>
      </section>
    </>
  )
}

export default App
