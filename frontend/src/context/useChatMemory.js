import { useContext } from 'react';
import ChatMemoryContext from './chatMemoryStore';

const useChatMemory = () => {
  const context = useContext(ChatMemoryContext);
  if (!context) {
    throw new Error('useChatMemory debe utilizarse dentro de ChatMemoryProvider.');
  }
  return context;
};

export default useChatMemory;
