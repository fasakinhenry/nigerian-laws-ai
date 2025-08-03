'use client'
import React, { useState, FormEvent, useRef, useEffect } from "react";
import styles from './style/home.module.css';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  isError?: boolean; 
}

const suggestionCards = [
  {
    title: "What are the legal requirements",
    subtitle: "for company registration in Nigeria?"
  },
  {
    title: "How do I obtain",
    subtitle: "a Certificate of Occupancy?"
  },
  {
    title: "What are the penalties",
    subtitle: "for tax evasion under Nigerian law?"
  },
  {
    title: "Explain the process",
    subtitle: "of property acquisition in Nigeria"
  }
];

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [isServerReady, setIsServerReady] = useState(false);

  const chatContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight
    }
  }, [messages])

  useEffect(() => {
    const checkServerStatus = async () => {
      try {
        const BackendUrl = process.env.NEXT_PUBLIC_BACKEND_URL;
        const response = await fetch(`${BackendUrl}/health`);
        const data = await response.json();

        if (response.ok && data.status === 'ready') {
          console.log("Backend is ready!");
          setIsServerReady(true);
          return;
        }

      } catch (error) {
        console.error("Failed to connect to backend, retrying...", error);
      }

      setTimeout(checkServerStatus, 2000);
    }
    checkServerStatus();
  }, [])

  const handleSuggestionClick = (suggestion: typeof suggestionCards[0]) => {
    const fullQuestion = `${suggestion.title} ${suggestion.subtitle}`;
    setInput(fullQuestion);
  };

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
      const BackendUrl = process.env.NEXT_PUBLIC_API_URL;
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

  if (!isServerReady) {
    return (
      <div className={styles.container}>
        <div className={styles.loadingContainer}>
          <p className={styles.loadingText}>Initializing Nigerian Laws AI Assistant...</p>
          <div className={styles.spinner}></div>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <div className={styles.chatBox} ref={chatContainerRef}>
        {messages.length === 0 ? (
          <div className={styles.emptyState}>
            <div className={styles.welcomeText}>
              <h1 className={styles.welcomeTitle}>Hello there!</h1>
              <p className={styles.welcomeSubtitle}>What Nigerian laws would you love to know today?</p>
            </div>
            <div className={styles.suggestionCards}>
              {suggestionCards.map((suggestion, index) => (
                <div 
                  key={index} 
                  className={styles.suggestionCard}
                  onClick={() => handleSuggestionClick(suggestion)}
                >
                  <h4>{suggestion.title}</h4>
                  <p>{suggestion.subtitle}</p>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <>
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
                  <div className={styles.loadingDots}>
                    <div className={styles.loadingDot}></div>
                    <div className={styles.loadingDot}></div>
                    <div className={styles.loadingDot}></div>
                  </div>
                </div>
              </div>
            )}
          </>
        )}
      </div>

      <form className={styles.inputForm} onSubmit={handleSubmit}>
        <div className={styles.inputContainer}>
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask a question about Nigerian Laws..."
            className={styles.inputField}
            disabled={loading}
          />
          <div className={styles.inputActions}>
            <button
              type="submit"
              className={styles.sendButton}
              disabled={loading || !input.trim()}
            >
              <svg className={styles.sendIcon} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
              </svg>
            </button>
          </div>
        </div>
      </form>
      <div className={styles.name}>
        <p>Developed by <span><a href="https://www.linkedin.com/in/franklin-n/" target="_blank">Franklin</a></span></p>
      </div>
    </div>
  );
}