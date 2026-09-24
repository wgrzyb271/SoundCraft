import { ToolBar } from './components/mainPage/Toolbar'
import { ChatSection } from './components/chatComponents/ChatSection'
import { AudioView } from './components/audioComponents/AudioView'
import './app.css'
import './fontStylesheet.css'
import { useState } from 'react'
import { uploadAudio } from './api/soundcraft'
function App() {

  const [audioFile, setAudioFile] = useState<File|null>(null);

  const handlePromptSubmit = async(newPrompt:string)=>{
    if(!audioFile){
      alert("Please upload an audio file first")
      return;
    }
    try{
      const data = await uploadAudio(audioFile, newPrompt)
      console.log("Request created:", data.request_id)
    } catch (error){
      console.log("Upload failed:",error)
      alert("Something went wrong while uploading the audio.");
    }
  }
  return (
    <>
    <ToolBar></ToolBar>
      <section id="center">
        <ChatSection onPromptSubmit={handlePromptSubmit}></ChatSection>
        <AudioView setAudioFile={setAudioFile} audioFile={audioFile}></AudioView>
      </section>
    </>
  )
}

export default App
