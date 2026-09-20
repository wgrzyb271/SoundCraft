import './styles/chatSection.css'
import { Message } from './Massage'
import { useState, useEffect, useRef } from 'react'

type ChatMessage ={
    sender: "user"|"agent"
    messageValue:string
}

function generateAgentResponse(length: number = 20): string {
    const letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'
    let result = ''

    for (let i = 0; i < length; i++) {
        const randomIndex = Math.floor(Math.random() * letters.length)
        result += letters[randomIndex]
    }

    return result
}

export function ChatSection(){
    const messagesEndRef = useRef<HTMLDivElement>(null)
     const [userMassage, setUserMassage] = useState('')
     
     const [messages, setMessages] = useState<ChatMessage[]>([
        {
            sender: "agent",
            messageValue: "Hello! How can I help?"
        }
     ])
     
    useEffect(() => {
         messagesEndRef.current?.scrollIntoView({
            behavior: 'smooth'})}, [messages])


     const handleSubmitUserMassage = (e: React.FormEvent<HTMLFormElement>)=>{
        e.preventDefault();
        if(!userMassage.trim()){
            return
        }

        setMessages(prev => [
            ...prev,
            {sender:"user",
            messageValue:userMassage
            }
        ])
        const response = generateAgentResponse() //in the future here will be async
        setMessages(prev => [
            ...prev,
            {sender:"agent",
            messageValue:response
            }
        ])

        setUserMassage('')
     }
    return (
        <>
        <section className = "chat-section">
            <div className = "message-view-div">
                {messages.map((message,index)=>(
                    <Message key={index} sender={message.sender} messageValue = {message.messageValue}></Message>
                ))
                }
            <div ref = {messagesEndRef}></div>
            </div>
            <div className = "user-input-div">
                <form onSubmit={handleSubmitUserMassage}>
                    <input type="text" placeholder='here will be user input' value={userMassage} onChange={e=>setUserMassage(e.target.value)}>
                    </input>
                    <input type="submit" value="send"></input>
                </form>
            </div>
        </section>
        </>
    )
}