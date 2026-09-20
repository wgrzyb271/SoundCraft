import './styles/message.css'
import '../../fontStylesheet.css'
type MessageProps= {
    sender: "user"|"agent", 
    messageValue:string, 
}

export function Message({sender, messageValue}:MessageProps){
    return (
        <div className={`message-${sender}-div manrope-regular`}>
            <p> {messageValue}</p>
        </div>
    )
}