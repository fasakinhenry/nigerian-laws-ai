'use client'
import React, { useState, FormEvent, useRef, useEffect } from "react";
import styles from './style/home.module.css';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  isError?: boolean; 
}


export default function Home() {

  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)

  const chatContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight
    }
  }, [messages])

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const userQuery = input;
    setInput('');
    setLoading(true)

    const newUserMessage: Message = { role: 'user', content: userQuery };
    setMessages(prevMessages => [...prevMessages, newUserMessage]);

    const initialAssistantMessage: Message = { role: 'assistant', content: '' }
    setMessages(prevMessages => [...prevMessages, initialAssistantMessage])

    try {
      const BackendUrl = process.env.NEXT_PUBLIC_PYTHON_BACKEND_URL;
      const response = await fetch(`${BackendUrl}/ask`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ question: userQuery })
      });

      if (!response.ok || !response.body) {
        throw new Error(`Failed to fetch response: ${response.status} ${response.statusText}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      let accumulatedContent = ""

      while (true) {
        const { done, value } = await reader.read();
        if (done) {
          console.log('Stream Complete')
          break;
        }

        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split('\n').filter(line => line.trim() !== '');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const jsonString = line.substring(6)
            try {
              const parsed = JSON.parse(jsonString)

              if (typeof parsed ==='object' && parsed != null) {
                if (parsed.type === 'chunk' && typeof parsed.content === 'string') {
                  accumulatedContent += parsed.content;
                  setMessages(prevMessages => {
                      const lastMessage = prevMessages[prevMessages.length - 1];
                      if (lastMessage && lastMessage.role === 'assistant') {
                          return [
                              ...prevMessages.slice(0, -1),
                              { ...lastMessage, content: accumulatedContent }
                          ];
                      }
                      return prevMessages;
                  });
                } else if (parsed.type === 'error' && typeof parsed.error === 'string') {
                  console.error("Backend error:", parsed.error);
                  setMessages(prevMessages => {
                      const lastMessage = prevMessages[prevMessages.length - 1];
                      if (lastMessage && lastMessage.role === 'assistant') {
                          return [
                              ...prevMessages.slice(0, -1),
                              { ...lastMessage, content: `${accumulatedContent}\n\nError: ${parsed.error}`, isError: true }
                          ];
                      }
                      return [...prevMessages, { role: 'assistant', content: `Error: ${parsed.error}`, isError: true }];
                  });
                  reader.cancel();
                  break;
              } 
            } else {
              console.warn("Received non-object data from SSE:", parsed);
            }
          } catch (jsonError) {
            console.error("Error parsing JSON from chunk:", jsonError, "Raw line:", line);
          }
        }
      }
    } 
    
    } catch (error) {
      console.error('Error fetching RAG response:', error);
      setMessages(prevMessages => {
        const lastMessage = prevMessages[prevMessages.length - 1];
        if (lastMessage && lastMessage.role === 'assistant') {
          return [
            ...prevMessages.slice(0, -1),
            { ...lastMessage, content: `Error: Could not stream response. Details: ${(error as Error).message}`, isError: true }
          ];
        }
        return [...prevMessages, { role: 'assistant', content: `Error: Could not stream response. Details: ${(error as Error).message}`, isError: true }];
      });
    } finally {
      setLoading(false);
    }
  };


  return (
    <div className={styles.container}>
      <h1 className={styles.header}>Nigerian Laws AI Assistant</h1>

      <div className={styles.chatBox} ref={chatContainerRef}>
        {messages.length === 0 && (
          <div className={styles.emptyState}>
            Welcome! Ask me anything about Nigerian laws.
          </div>
        )}
        {messages.map((msg, index) => (
          <div key={index} className={`${styles.message} ${msg.role === 'user' ? styles.userMessage : styles.assistantMessage}`}>
            <div className={`${styles.messageContent} ${msg.isError ? styles.error : ''}`}>
              <p className={styles.messageText}>{msg.content}</p>
            </div>
          </div>
        ))}
        {loading && (
          <div className={`${styles.message} ${styles.assistantMessage}`}>
            <div className={styles.messageContent}>
              <p>Thinking...</p>
            </div>
          </div>
        )}
      </div>

      <form className={styles.inputForm} onSubmit={handleSubmit}>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about Nigerian laws..."
          className={styles.inputField}
          disabled={loading}
        />
        <button
          type="submit"
          className={styles.sendButton}
          disabled={loading}
        >
          Send
        </button>
      </form>
    </div>
  );
}
