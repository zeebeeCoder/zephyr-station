'use client';

import { useChat } from '@ai-sdk/react';
import type { UIMessage, ToolUIPart } from 'ai';
import { DefaultChatTransport } from 'ai';
import { CopyIcon, CheckIcon, RefreshCwIcon, SquareIcon } from 'lucide-react';
import { useState, useCallback, type ReactNode } from 'react';
import Link from 'next/link';

// Removed Conversation wrapper - using full-page scroll instead
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
  "What's the forecast?",
  "Should I open the windows?",
];

// Weather-specific icons and formatting
const TOOL_CONFIG: Record<string, { icon: string; label: string }> = {
  get_current: { icon: '🌡️', label: 'Current Reading' },
  query_range: { icon: '📊', label: 'Time Range Query' },
  compare_periods: { icon: '📈', label: 'Period Comparison' },
  execute_sql: { icon: '🔍', label: 'Database Query' },
  get_forecast: { icon: '🔮', label: 'Weather Forecast' },
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

  // For forecast, show day cards
  if (toolName === 'get_forecast' && Array.isArray(output)) {
    return (
      <div className="grid grid-cols-3 gap-2 text-sm p-2">
        {output.map((day: { dayName: string; date: string; conditionEmoji: string; condition: string; tempMax: number; tempMin: number; precipChance: number }) => (
          <div key={day.date} className="rounded-md bg-muted/50 p-2 text-center space-y-1">
            <div className="font-medium">{day.dayName}</div>
            <div className="text-2xl">{day.conditionEmoji}</div>
            <div className="text-xs text-muted-foreground">{day.condition}</div>
            <div className="font-semibold">{day.tempMax}° / <span className="text-muted-foreground">{day.tempMin}°</span></div>
            <div className="text-xs">Rain: {day.precipChance}%</div>
          </div>
        ))}
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
function MessagePart({ part, index, role }: { part: UIMessage['parts'][number]; index: number; role: UIMessage['role'] }) {
  if (part.type === 'text') {
    return <MessageResponse key={index} enableSemanticParsing={role === 'assistant'}>{part.text}</MessageResponse>;
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
      <header className="shrink-0 border-b px-4 py-3 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold flex items-center gap-2">
            <span>🌤️</span>
            <span>Zephyr Weather Station</span>
          </h1>
          <p className="text-sm text-muted-foreground">
            Ask about your local weather conditions
          </p>
        </div>
        <Link
          href="/forecast"
          className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors px-3 py-1.5 rounded-md border border-border hover:bg-muted"
        >
          🔮 Forecast
        </Link>
      </header>

      {/* Sticky input area at bottom */}
      <div className="fixed bottom-0 left-0 right-0 bg-gradient-to-t from-background via-background to-transparent pt-6 pb-4">
        <div className="max-w-3xl mx-auto px-4">
          {/* Error display */}
          {error && (
            <div className="mb-3 px-4 py-3 bg-destructive/10 text-destructive rounded-md text-sm">
              <p className="font-medium">Something went wrong</p>
              <p className="text-xs mt-1 opacity-80">{error.message}</p>
              <Button variant="outline" size="sm" className="mt-2" onClick={() => regenerate()}>
                Try again
              </Button>
            </div>
          )}
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

      {/* Subtle branding - top left */}
      <div className="fixed top-4 left-4 text-xs text-muted-foreground/50 flex items-center gap-1.5">
        <span>🌤️</span>
        <span>Zephyr</span>
      </div>
    </div>
  );
}
