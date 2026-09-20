import './styles/message.css'
import '../../fontStylesheet.css'
type MessageProps= {
    sender: "user"|"agent", 
    messageValue:string, 
}

export function Message({sender, messageValue}:MessageProps){
    return (
        <div className={`manrope-regular message-${sender}-div`}>
            <p> {messageValue}</p>
        </div>
    )
}