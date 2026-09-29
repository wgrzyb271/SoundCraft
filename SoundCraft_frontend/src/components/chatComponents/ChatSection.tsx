import { useEffect, useRef, useState } from 'react'
import uploadIcon from '../../assets/send_icon.svg'
import '../../fontStylesheet.css'
import { Message } from './Massage'
import './styles/chatSection.css'

type ChatMessage = {
  sender: 'user' | 'agent'
  messageValue: string
}

type ChatSectionProps = {
  onPromptSubmit: (prompt: string) => Promise<boolean>
  agentResponse: Record<string, unknown> | null
}

export function ChatSection({ onPromptSubmit, agentResponse }: ChatSectionProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const [userMessage, setUserMessage] = useState('')
  const [messages, setMessages] = useState<ChatMessage[]>([
    { sender: 'agent', messageValue: 'Hello! How can I help?' },
  ])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  useEffect(() => {
    if (!agentResponse) return
    const message =
      typeof agentResponse.error_message === 'string'
        ? agentResponse.error_message
        : agentResponse.execution_code === 'PASSED'
          ? 'Audio processed successfully.'
          : typeof agentResponse.message === 'string'
            ? agentResponse.message
            : JSON.stringify(agentResponse)
    const timer = window.setTimeout(() => {
      setMessages(previous => [...previous, { sender: 'agent', messageValue: message }])
    }, 0)
    return () => window.clearTimeout(timer)
  }, [agentResponse])

  const handleSubmitUserMessage = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const message = userMessage.trim()
    if (!message) return

    if (await onPromptSubmit(message)) {
      setMessages(previous => [...previous, { sender: 'user', messageValue: message }])
      setUserMessage('')
    }
  }

  return (
    <section className="chat-section">
      <div className="message-view-div">
        {messages.map((message, index) => (
          <Message key={index} sender={message.sender} messageValue={message.messageValue} />
        ))}
        <div ref={messagesEndRef} />
      </div>
      <div className="user-input-div">
        <form onSubmit={handleSubmitUserMessage}>
          <input
            className="manrope-regular"
            type="text"
            placeholder="Message..."
            value={userMessage}
            onChange={event => setUserMessage(event.target.value)}
          />
          <button type="submit" className="submit-button">
            <img src={uploadIcon} alt="Send" />
          </button>
        </form>
      </div>
    </section>
  )
}
