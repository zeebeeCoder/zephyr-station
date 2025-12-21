'use client';

import { useChat } from '@ai-sdk/react';
import type { UIMessage, ToolUIPart } from 'ai';
import { DefaultChatTransport } from 'ai';
import { CopyIcon, CheckIcon, RefreshCwIcon, SquareIcon } from 'lucide-react';
import { useState, useCallback, type ReactNode } from 'react';

import {
  Conversation,
  ConversationContent,
  ConversationScrollButton,
} from '@/components/ai-elements/conversation';
import {
  Message,
  MessageContent,
  MessageActions,
  MessageAction,
  MessageResponse,
} from '@/components/ai-elements/message';
import {
  PromptInput,
  PromptInputTextarea,
  PromptInputFooter,
  PromptInputTools,
  PromptInputSubmit,
} from '@/components/ai-elements/prompt-input';
import { Suggestions, Suggestion } from '@/components/ai-elements/suggestion';
import {
  Tool,
  ToolHeader,
  ToolContent,
  ToolInput,
  ToolOutput,
} from '@/components/ai-elements/tool';
import {
  Reasoning,
  ReasoningTrigger,
  ReasoningContent,
} from '@/components/ai-elements/reasoning';
import { Button } from '@/components/ui/button';

const SUGGESTIONS = [
  "What's the current temperature?",
  "How's the air quality?",
  "Is it warmer than yesterday?",
  "Should I open the windows?",
];

// Weather-specific icons and formatting
const TOOL_CONFIG: Record<string, { icon: string; label: string }> = {
  get_current: { icon: '🌡️', label: 'Current Reading' },
  query_range: { icon: '📊', label: 'Time Range Query' },
  compare_periods: { icon: '📈', label: 'Period Comparison' },
  execute_sql: { icon: '🔍', label: 'Database Query' },
};

function formatWeatherOutput(toolName: string, output: unknown): ReactNode {
  if (!output) return null;

  // For weather readings, show a nice grid
  if (toolName === 'get_current' && Array.isArray(output)) {
    const reading = output[0];
    if (!reading) return <span className="text-muted-foreground">No readings available</span>;

    return (
      <div className="grid grid-cols-2 gap-2 text-sm p-2">
        {reading.temperature_c !== null && (
          <div className="flex items-center gap-2">
            <span>🌡️</span>
            <span>{reading.temperature_c}°C</span>
          </div>
        )}
        {reading.humidity_pct !== null && (
          <div className="flex items-center gap-2">
            <span>💧</span>
            <span>{reading.humidity_pct}%</span>
          </div>
        )}
        {reading.pm25 !== null && (
          <div className="flex items-center gap-2">
            <span>🌫️</span>
            <span>PM2.5: {reading.pm25}</span>
          </div>
        )}
        {reading.pressure_hpa !== null && (
          <div className="flex items-center gap-2">
            <span>🔵</span>
            <span>{reading.pressure_hpa} hPa</span>
          </div>
        )}
      </div>
    );
  }

  // For comparison, show both periods
  if (toolName === 'compare_periods' && typeof output === 'object') {
    const data = output as { period1?: { avg_temperature?: number }; period2?: { avg_temperature?: number } };
    return (
      <div className="text-sm space-y-1 p-2">
        <div>Period 1: {data.period1?.avg_temperature?.toFixed(1)}°C avg</div>
        <div>Period 2: {data.period2?.avg_temperature?.toFixed(1)}°C avg</div>
      </div>
    );
  }

  return null;
}

// Part renderer component
function MessagePart({ part, index }: { part: UIMessage['parts'][number]; index: number }) {
  if (part.type === 'text') {
    return <MessageResponse key={index}>{part.text}</MessageResponse>;
  }

  if (part.type === 'reasoning') {
    const reasoningPart = part as { type: 'reasoning'; text: string };
    return (
      <Reasoning key={index} isStreaming={false}>
        <ReasoningTrigger />
        <ReasoningContent>{reasoningPart.text}</ReasoningContent>
      </Reasoning>
    );
  }

  if (part.type.startsWith('tool-')) {
    const toolPart = part as ToolUIPart;
    const toolName = part.type.replace('tool-', '');
    const config = TOOL_CONFIG[toolName] || { icon: '🔧', label: toolName };
    const customOutput = formatWeatherOutput(toolName, toolPart.output);

    return (
      <Tool key={index} defaultOpen={toolPart.state === 'output-available'}>
        <ToolHeader
          title={`${config.icon} ${config.label}`}
          type={toolPart.type}
          state={toolPart.state}
        />
        <ToolContent>
          <ToolInput input={toolPart.input} />
          {customOutput ? (
            <div className="p-4">
              <h4 className="font-medium text-muted-foreground text-xs uppercase tracking-wide mb-2">
                Result
              </h4>
              <div className="rounded-md bg-muted/50">{customOutput}</div>
            </div>
          ) : (
            <ToolOutput output={toolPart.output} errorText={toolPart.errorText} />
          )}
        </ToolContent>
      </Tool>
    );
  }

  if (part.type === 'step-start' && index > 0) {
    return <hr key={index} className="my-4 border-border/50" />;
  }

  return null;
}

// Copy button with feedback
function CopyButton({ content }: { content: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard API not available
    }
  }, [content]);

  return (
    <MessageAction tooltip="Copy message" onClick={handleCopy}>
      {copied ? <CheckIcon className="size-4" /> : <CopyIcon className="size-4" />}
    </MessageAction>
  );
}

function getMessageText(message: UIMessage): string {
  return message.parts
    .filter((part): part is { type: 'text'; text: string } => part.type === 'text')
    .map((part) => part.text)
    .join('\n');
}

export function Chat() {
  const { messages, sendMessage, stop, regenerate, status, error } = useChat({
    transport: new DefaultChatTransport({ api: '/api/chat' }),
    experimental_throttle: 50,
  });

  const handleSend = (message: { text: string; files: unknown[] }) => {
    if (message.text.trim()) {
      sendMessage({ text: message.text });
    }
  };

  const handleSuggestion = (suggestion: string) => {
    sendMessage({ text: suggestion });
  };

  const isLoading = status === 'submitted' || status === 'streaming';

  return (
    <div className="flex flex-col h-screen max-w-3xl mx-auto">
      {/* Header */}
      <header className="shrink-0 border-b px-4 py-3">
        <h1 className="text-xl font-semibold flex items-center gap-2">
          <span>🌤️</span>
          <span>Zephyr Weather Station</span>
        </h1>
        <p className="text-sm text-muted-foreground">
          Ask about your local weather conditions
        </p>
      </header>

      {/* Conversation area */}
      <div className="flex-1 overflow-hidden">
        <Conversation className="h-full">
          <ConversationContent className="min-h-full">
            {messages.length === 0 ? (
              <div className="flex flex-col items-center justify-center min-h-[50vh] gap-4 py-8">
                <span className="text-4xl">🌤️</span>
                <div className="text-center space-y-1">
                  <h3 className="font-medium">Welcome to Zephyr</h3>
                  <p className="text-muted-foreground text-sm">
                    Ask about your local weather conditions
                  </p>
                </div>
                <div className="flex flex-col items-center gap-4 pt-4">
                  <p className="text-muted-foreground text-sm">Try asking:</p>
                  <Suggestions>
                    {SUGGESTIONS.map((suggestion) => (
                      <Suggestion
                        key={suggestion}
                        suggestion={suggestion}
                        onClick={handleSuggestion}
                      />
                    ))}
                  </Suggestions>
                </div>
              </div>
            ) : (
              messages.map((message) => (
                <Message key={message.id} from={message.role}>
                  <MessageContent>
                    {message.parts.map((part, idx) => (
                      <MessagePart key={idx} part={part} index={idx} />
                    ))}
                  </MessageContent>
                  {message.role === 'assistant' && (
                    <MessageActions>
                      <CopyButton content={getMessageText(message)} />
                      <MessageAction tooltip="Regenerate" onClick={() => regenerate()}>
                        <RefreshCwIcon className="size-4" />
                      </MessageAction>
                    </MessageActions>
                  )}
                </Message>
              ))
            )}
          </ConversationContent>
          <ConversationScrollButton />
        </Conversation>
      </div>

      {/* Error display */}
      {error && (
        <div className="shrink-0 px-4 py-3 mx-4 mb-2 bg-destructive/10 text-destructive rounded-md text-sm">
          <p className="font-medium">Something went wrong</p>
          <p className="text-xs mt-1 opacity-80">{error.message}</p>
          <Button variant="outline" size="sm" className="mt-2" onClick={() => regenerate()}>
            Try again
          </Button>
        </div>
      )}

      {/* Input area */}
      <div className="shrink-0 border-t p-4">
        <PromptInput onSubmit={handleSend}>
          <PromptInputTextarea placeholder="Ask about the weather..." disabled={isLoading} />
          <PromptInputFooter>
            <PromptInputTools />
            {isLoading ? (
              <Button type="button" variant="secondary" size="icon-sm" onClick={stop}>
                <SquareIcon className="size-4" />
              </Button>
            ) : (
              <PromptInputSubmit status={status} />
            )}
          </PromptInputFooter>
        </PromptInput>
      </div>
    </div>
  );
}
