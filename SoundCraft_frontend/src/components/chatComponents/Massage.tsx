import './styles/message.css'

type MessageProps= {
    sender: "user"|"agent", 
    messageValue:string, 
}

export function Message({sender, messageValue}:MessageProps){
    return (
        <div className={`message-${sender}-div`}>
            <p> {messageValue}</p>
        </div>
    )
}