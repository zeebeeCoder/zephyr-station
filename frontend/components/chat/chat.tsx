'use client';

import { useChat } from '@ai-sdk/react';
import { DefaultChatTransport } from 'ai';
import { useEffect, useRef } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { ChatMessage } from './message';
import { ChatInput } from './input';

const EXAMPLE_PROMPTS = [
  "What's the current temperature?",
  "How's the air quality?",
  "Is it warmer than yesterday?",
  "Should I open the windows?",
];

export function Chat() {
  const scrollRef = useRef<HTMLDivElement>(null);

  const { messages, sendMessage, stop, status, error } = useChat({
    transport: new DefaultChatTransport({ api: '/api/chat' }),
    experimental_throttle: 50,
  });

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSend = (text: string) => {
    sendMessage({ text });
  };

  return (
    <Card className="flex flex-col h-[calc(100vh-4rem)] max-w-3xl mx-auto">
      <CardHeader className="pb-4">
        <CardTitle className="flex items-center gap-2">
          <span>🌤️</span>
          <span>Zephyr Weather Station</span>
        </CardTitle>
        <CardDescription>
          Ask about your local weather conditions
        </CardDescription>
      </CardHeader>

      <CardContent className="flex-1 flex flex-col gap-4 overflow-hidden pb-4">
        {/* Messages area */}
        <ScrollArea
          ref={scrollRef}
          className="flex-1 px-1 -mx-1"
        >
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-center py-8">
              <p className="text-muted-foreground mb-4">Try asking:</p>
              <div className="flex flex-wrap gap-2 justify-center max-w-md">
                {EXAMPLE_PROMPTS.map((prompt) => (
                  <button
                    key={prompt}
                    onClick={() => handleSend(prompt)}
                    className="px-3 py-1.5 text-sm bg-muted hover:bg-muted/80 rounded-full transition-colors"
                  >
                    {prompt}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="space-y-2">
              {messages.map((message) => (
                <ChatMessage key={message.id} message={message} />
              ))}

              {/* Streaming indicator */}
              {status === 'streaming' && (
                <div className="flex items-center gap-2 text-sm text-muted-foreground pl-2">
                  <span className="animate-pulse">●</span>
                  <span>Zephyr is thinking...</span>
                </div>
              )}

              {status === 'submitted' && (
                <div className="text-sm text-muted-foreground pl-2">
                  Sending message...
                </div>
              )}
            </div>
          )}
        </ScrollArea>

        {/* Error display */}
        {error && (
          <div className="px-4 py-3 bg-destructive/10 text-destructive rounded-md text-sm">
            <p className="font-medium">Something went wrong</p>
            <p className="text-xs mt-1 opacity-80">{error.message}</p>
          </div>
        )}

        {/* Input area */}
        <ChatInput
          onSend={handleSend}
          onStop={stop}
          status={status}
        />
      </CardContent>
    </Card>
  );
}
