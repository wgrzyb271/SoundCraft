import { ToolBar } from './components/mainPage/Toolbar'
import { ChatSection } from './components/chatComponents/ChatSection'
import { AudioView } from './components/audioComponents/AudioView'
import './app.css'
import './fontStylesheet.css'
function App() {

  return (
    <>
    <ToolBar></ToolBar>
      <section id="center">
        <ChatSection></ChatSection>
        <AudioView></AudioView>
      </section>
    </>
  )
}

export default App
