'use client';

import { FormEvent, useState, KeyboardEvent } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

interface ChatInputProps {
  onSend: (text: string) => void;
  onStop?: () => void;
  status: 'ready' | 'submitted' | 'streaming' | 'error';
  disabled?: boolean;
}

export function ChatInput({ onSend, onStop, status, disabled }: ChatInputProps) {
  const [input, setInput] = useState('');

  const isLoading = status === 'submitted' || status === 'streaming';
  const canSend = status === 'ready' && input.trim() && !disabled;

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (canSend) {
      onSend(input.trim());
      setInput('');
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey && canSend) {
      e.preventDefault();
      onSend(input.trim());
      setInput('');
    }
  };

  return (
    <form onSubmit={handleSubmit} className="flex gap-2">
      <Input
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Ask about the weather..."
        disabled={isLoading || disabled}
        className="flex-1"
      />

      {isLoading && onStop ? (
        <Button type="button" variant="secondary" onClick={onStop}>
          Stop
        </Button>
      ) : (
        <Button type="submit" disabled={!canSend}>
          Send
        </Button>
      )}
    </form>
  );
}
