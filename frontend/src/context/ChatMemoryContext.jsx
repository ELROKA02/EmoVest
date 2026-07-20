import { useCallback, useMemo, useRef, useState } from 'react';
import ChatMemoryContext from './chatMemoryStore';

export const ChatMemoryProvider = ({ children }) => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [accountId, setAccountId] = useState(null);
  const [accountName, setAccountName] = useState('');
  const [pendingQuestion, setPendingQuestion] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [isResetting, setIsResetting] = useState(false);
  const [statusText, setStatusText] = useState('');

  const sessionIdRef = useRef(null);
  const currentRequestRef = useRef(null);
  const chatOwnerTokenRef = useRef(null);

  const clearChatMemory = useCallback(() => {
    currentRequestRef.current?.abort();
    currentRequestRef.current = null;
    sessionIdRef.current = null;
    setMessages([]);
    setInput('');
    setAccountId(null);
    setAccountName('');
    setPendingQuestion('');
    setIsStreaming(false);
    setIsResetting(false);
    setStatusText('');
  }, []);

  const value = useMemo(() => ({
    messages,
    setMessages,
    input,
    setInput,
    accountId,
    setAccountId,
    accountName,
    setAccountName,
    pendingQuestion,
    setPendingQuestion,
    isStreaming,
    setIsStreaming,
    isResetting,
    setIsResetting,
    statusText,
    setStatusText,
    sessionIdRef,
    currentRequestRef,
    chatOwnerTokenRef,
    clearChatMemory,
  }), [
    accountId,
    accountName,
    clearChatMemory,
    input,
    isResetting,
    isStreaming,
    messages,
    pendingQuestion,
    statusText,
  ]);

  return (
    <ChatMemoryContext.Provider value={value}>
      {children}
    </ChatMemoryContext.Provider>
  );
};
