'use client';

import type { UIMessage } from 'ai';
import { cn } from '@/lib/utils';
import { ToolInvocation } from './tool-invocation';

interface ChatMessageProps {
  message: UIMessage;
}

export function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === 'user';

  return (
    <div
      className={cn(
        'flex flex-col gap-1 mb-4',
        isUser ? 'items-end' : 'items-start'
      )}
    >
      {/* Role indicator */}
      <div
        className={cn(
          'text-xs font-medium px-2',
          isUser ? 'text-primary' : 'text-muted-foreground'
        )}
      >
        {isUser ? 'You' : 'Zephyr'}
      </div>

      {/* Message bubble */}
      <div
        className={cn(
          'max-w-[85%] rounded-lg px-4 py-3',
          isUser
            ? 'bg-primary text-primary-foreground'
            : 'bg-muted text-foreground'
        )}
      >
        {message.parts?.map((part, idx) => {
          // Text content
          if (part.type === 'text') {
            return (
              <p key={idx} className="whitespace-pre-wrap">
                {part.text}
              </p>
            );
          }

          // Tool invocations (match tool-* pattern)
          if (part.type.startsWith('tool-')) {
            const toolPart = part as {
              type: string;
              toolCallId: string;
              state: 'input-streaming' | 'input-available' | 'output-available' | 'output-error';
              input?: unknown;
              output?: unknown;
              errorText?: string;
            };
            const toolName = part.type.replace('tool-', '');

            return (
              <ToolInvocation
                key={idx}
                toolName={toolName}
                state={toolPart.state}
                input={toolPart.input}
                output={toolPart.output}
                errorText={toolPart.errorText}
              />
            );
          }

          // Step separator
          if (part.type === 'step-start' && idx > 0) {
            return <hr key={idx} className="my-2 border-border/50" />;
          }

          // Reasoning (for models that support it)
          if (part.type === 'reasoning') {
            const reasoningPart = part as { type: 'reasoning'; text: string };
            return (
              <details key={idx} className="text-xs mt-2">
                <summary className="cursor-pointer text-muted-foreground hover:text-foreground">
                  💭 Show reasoning
                </summary>
                <pre className="mt-1 p-2 bg-background/50 rounded text-xs overflow-x-auto">
                  {reasoningPart.text}
                </pre>
              </details>
            );
          }

          return null;
        })}
      </div>
    </div>
  );
}
