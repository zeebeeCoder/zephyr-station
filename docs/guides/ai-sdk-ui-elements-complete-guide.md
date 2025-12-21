# AI SDK UI + AI Elements - Complete Chatbot Agent Reference
**Latest AI SDK v5.0+ | AI Elements 2025 | Production-Ready Examples**

---

## Table of Contents
1. [AI Elements Components (NEW!)](#ai-elements-components)
2. [AI Elements Installation](#ai-elements-installation)
3. [Quick Start](#quick-start)
4. [Core Concepts](#core-concepts)
5. [API Reference](#api-reference)
6. [Frontend Implementation](#frontend-implementation)
7. [Backend Implementation](#backend-implementation)
8. [Tool Integration](#tool-integration)
9. [Advanced Patterns](#advanced-patterns)
10. [Error Handling](#error-handling)
11. [Performance Optimization](#performance-optimization)
12. [Type Safety](#type-safety)

---

## AI Elements Components

**AI Elements** is a purpose-built component library on top of shadcn/ui for building AI-native applications faster. It provides 20+ pre-built components specifically designed for conversational AI patterns.

### Complete Component List (2025)

| Component | Purpose | Type |
|-----------|---------|------|
| **Conversation** | Auto-scrolling chat container with scroll-to-bottom button | Layout |
| **Message** | Chat message containers with role-based styling (user/AI) | Display |
| **MessageContent** | Wrapper for message parts (text, files, etc.) | Display |
| **Response** | Streaming-optimized markdown renderer with syntax highlighting | Display |
| **PromptInput** | Auto-resizing textarea with toolbar and attachment support | Input |
| **Actions** | Interactive action buttons (copy, regenerate, edit) | Interactive |
| **Suggestion** | Scrollable quick-prompt pills below input | Interactive |
| **Tool** | Collapsible tool execution display with status tracking | Display |
| **Reasoning** | Collapsible AI reasoning/thought process display | Display |
| **Sources** | Collapsible source citations and references | Display |
| **Branch** | Response variation navigation for multi-response conversations | Navigation |
| **Attachment** | File upload and display component | Input |
| **Citation** | Inline hoverable citations with source information | Display |
| **Loader** | Custom loading spinners for streaming states | Feedback |
| **TypingIndicator** | "AI is typing" animation | Feedback |
| **ChainOfThought** | Visualize reasoning steps and thought processes | Display |
| **Context** | Display AI model context window, tokens, and cost | Feedback |
| **Plan** | Plan and task planning display | Display |
| **Queue** | Message and todo queue with attachments | Display |
| **Task** | Collapsible task lists with file references and progress | Display |
| **Shimmer** | Text shimmer animation effect | Animation |

### Core Components for Basic Chat

Start with these 5 essentials:
```bash
npx ai-elements@latest add conversation message response prompt-input actions
```

### Extended Components for Advanced Features

Add these for richer interactions:
```bash
npx ai-elements@latest add suggestion reasoning tool branch attachment sources
```

---

## AI Elements Installation

### Prerequisites

- Node.js 18+
- Next.js project with AI SDK installed
- shadcn/ui already configured
- Tailwind CSS 4 configured
- React 19 (recommended)

### Method 1: AI Elements CLI (Recommended)

```bash
# Install all components at once
npx ai-elements@latest

# Install specific component
npx ai-elements@latest add message

# Install multiple components
npx ai-elements@latest add conversation message response prompt-input actions reasoning
```

### Method 2: shadcn/ui CLI

```bash
# Install all components
npx shadcn@latest add https://registry.ai-sdk.dev/all.json

# Install specific component
npx shadcn@latest add https://registry.ai-sdk.dev/conversation.json
```

### Environment Setup (Optional)

AI Gateway provides $5/month free credits and avoids per-provider API keys:

```env
# .env.local
AI_GATEWAY_API_KEY=your_gateway_key
```

Get API key: https://gateway.ai.cloud.google.com

---

## Quick Start

### 5-Minute Basic Chat

**1. Install components:**
```bash
npx ai-elements@latest add conversation message response prompt-input actions
```

**2. Client component (`app/page.tsx`):**
```typescript
'use client';

import { useChat } from '@ai-sdk/react';
import { Conversation } from '@/components/ai-elements/conversation';
import { Message } from '@/components/ai-elements/message';
import { Response } from '@/components/ai-elements/response';
import { PromptInput } from '@/components/ai-elements/prompt-input';

export default function ChatPage() {
  const { messages, sendMessage, status } = useChat({
    api: '/api/chat',
  });

  return (
    <div className="flex flex-col h-screen">
      <Conversation>
        {messages.map(message => (
          <Message key={message.id} role={message.role}>
            {message.role === 'assistant' ? (
              <Response>{message.content}</Response>
            ) : (
              message.content
            )}
          </Message>
        ))}
      </Conversation>

      <PromptInput
        onSend={(text) => sendMessage({ text })}
        disabled={status !== 'ready'}
      />
    </div>
  );
}
```

**3. Server handler (`app/api/chat/route.ts`):**
```typescript
import { streamText } from 'ai';
import { openai } from '@ai-sdk/openai';

export const maxDuration = 30;

export async function POST(req: Request) {
  const { messages } = await req.json();

  const result = streamText({
    model: openai('gpt-4o-mini'),
    system: 'You are a helpful assistant.',
    messages,
  });

  return result.toDataStreamResponse();
}
```

That's it! You have a production-ready chat interface.

---

## Core Concepts

### Message Structure (v5.0+)

The `UIMessage` structure uses **parts** for flexible rendering:

```typescript
interface UIMessage {
  id: string;
  role: 'system' | 'user' | 'assistant';
  parts: UIMessagePart[];
  metadata?: unknown;
  status?: 'submitted' | 'streaming' | 'ready' | 'error';
}

type UIMessagePart = 
  | { type: 'text'; text: string }
  | { type: 'tool-[name]'; toolCallId: string; state: 'input-streaming' | 'input-available' | 'output-available' | 'output-error'; input?: unknown; output?: unknown; errorText?: string }
  | { type: 'file'; filename: string; mediaType: string; url: string }
  | { type: 'data'; data: unknown }
  | { type: 'step-start' }
  | { type: 'source-url'; url: string; title?: string }
  | { type: 'reasoning'; text: string };
```

### Chat Status States

```
submitted → streaming → ready (success)
                    ↓
                  error (failure)
```

| State | Meaning | Can Submit |
|-------|---------|-----------|
| `ready` | Idle, waiting for input | ✅ Yes |
| `submitted` | Request sent, awaiting response | ❌ No |
| `streaming` | Response being received | ❌ No (can stop) |
| `error` | Request failed | ✅ Yes (retry) |

### Transport Architecture (v5.0+)

```
Client: useChat + DefaultChatTransport
        ↓ POST /api/chat with messages
Server: POST handler
        ↓ streamText() with tools
Client: receives streamed UIMessage
```

---

## API Reference

### useChat Hook

```typescript
const {
  // State
  messages,           // UIMessage[]
  status,             // 'ready' | 'submitted' | 'streaming' | 'error'
  error,              // Error | undefined
  id,                 // string (chat session ID)
  
  // Methods
  sendMessage,        // (msg: string | CreateUIMessage, options?: ChatRequestOptions) => void
  stop,               // () => void
  regenerate,         // (options?: { messageId?: string }) => void
  clearError,         // () => void
  resumeStream,       // () => void
  addToolOutput,      // (options: ToolOutputOptions) => void
  setMessages,        // (messages: UIMessage[] | ((msgs: UIMessage[]) => UIMessage[])) => void
  
  // Callbacks
  onToolCall,         // ({ toolCall }: { toolCall: ToolCall }) => void | Promise<void>
  onFinish,           // ({ message, messages, isAbort, isDisconnect, isError, finishReason }) => void
  onError,            // (error: Error) => void
  onData,             // (dataPart: DataUIPart) => void
} = useChat(options);
```

### useChat Options

```typescript
interface UseChatOptions {
  // Transport configuration
  transport?: ChatTransport;
  api?: string;                          // default: '/api/chat'
  credentials?: RequestCredentials;
  headers?: Record<string, string> | (() => Record<string, string>);
  body?: Record<string, any> | (() => Record<string, any>);
  
  // State management
  id?: string;
  messages?: UIMessage[];
  resume?: boolean;                      // resume interrupted streams
  
  // Tool handling
  onToolCall?: ({ toolCall: ToolCall }) => void | Promise<void>;
  sendAutomaticallyWhen?: (options: { messages: UIMessage[] }) => boolean;
  
  // Callbacks
  onFinish?: (options: OnFinishOptions) => void;
  onError?: (error: Error) => void;
  onData?: (dataPart: DataUIPart) => void;
  
  // Performance
  experimental_throttle?: number;        // throttle UI updates in ms
}
```

### AI Elements Component Props

#### Conversation Component

```typescript
<Conversation
  messages={messages}
  isLoading={status === 'streaming'}
  isError={!!error}
  scrollBehavior="auto" | "smooth" // default: 'smooth'
  emptyState={<div>No messages yet</div>}
>
  {/* Message components go here */}
</Conversation>
```

#### Message Component

```typescript
<Message
  role="user" | "assistant"
  avatar={<img src="..." />}
  actions={<MessageActions />}
  metadata={{ timestamp: Date.now() }}
>
  {/* Content or Response component */}
</Message>
```

#### Response Component

```typescript
<Response
  markdown={true}           // default: true (renders markdown)
  syntaxHighlight={true}    // default: true (code highlighting)
  streaming={true}          // default: true (optimized for streaming)
>
  {/* Raw markdown content */}
</Response>
```

#### PromptInput Component

```typescript
<PromptInput
  onSend={(text, attachments) => handleSend(text, attachments)}
  onAttach={(files) => handleAttach(files)}
  disabled={false}
  placeholder="Type a message..."
  maxHeight={200}
  attachmentTypes="image/*,text/*"
/>
```

#### Tool Component

```typescript
<Tool
  name="calculatePrice"
  status="running" | "success" | "error"
  input={{ items: [...] }}
  output={123.45}
  error="Failed to calculate"
/>
```

#### Reasoning Component

```typescript
<Reasoning
  content="Let me think about this step by step..."
  collapsed={true}      // starts collapsed
  expandText="Show reasoning"
  collapseText="Hide reasoning"
/>
```

---

## Frontend Implementation

### Complete Chat with AI Elements

```typescript
'use client';

import { useChat } from '@ai-sdk/react';
import { Conversation, ConversationContent, ConversationEmptyState } from '@/components/ai-elements/conversation';
import { Message } from '@/components/ai-elements/message';
import { Response } from '@/components/ai-elements/response';
import { PromptInput } from '@/components/ai-elements/prompt-input';
import { Actions } from '@/components/ai-elements/actions';
import { Suggestion } from '@/components/ai-elements/suggestion';
import { Tool } from '@/components/ai-elements/tool';
import { Reasoning } from '@/components/ai-elements/reasoning';
import { Sources } from '@/components/ai-elements/sources';

export default function ChatPage() {
  const { messages, sendMessage, status, error, stop, reload } = useChat({
    api: '/api/chat',
  });

  return (
    <div className="flex flex-col h-screen bg-white">
      <Conversation>
        <ConversationContent>
          {messages.map(message => (
            <Message
              key={message.id}
              role={message.role}
              avatar={message.role === 'assistant' ? '🤖' : '👤'}
              actions={
                message.role === 'assistant' ? (
                  <Actions
                    onCopy={() => {
                      const text = message.parts
                        .filter(p => p.type === 'text')
                        .map(p => p.text)
                        .join('\n');
                      navigator.clipboard.writeText(text);
                    }}
                  />
                ) : null
              }
            >
              {message.parts.map((part, idx) => {
                if (part.type === 'text') {
                  return <Response key={idx}>{part.text}</Response>;
                }
                
                if (part.type === 'reasoning') {
                  return (
                    <Reasoning key={idx} content={part.text} collapsed />
                  );
                }
                
                if (part.type === 'source-url') {
                  return (
                    <Sources
                      key={idx}
                      sources={[{
                        title: part.title,
                        url: part.url,
                      }]}
                    />
                  );
                }
                
                if (part.type?.startsWith('tool-')) {
                  const toolName = part.type.replace('tool-', '');
                  return (
                    <Tool
                      key={idx}
                      name={toolName}
                      status={
                        part.state === 'input-streaming' ? 'running' :
                        part.state === 'output-available' ? 'success' :
                        part.state === 'output-error' ? 'error' : 'running'
                      }
                      input={part.input}
                      output={part.output}
                      error={part.errorText}
                    />
                  );
                }
                
                return null;
              })}
            </Message>
          ))}
        </ConversationContent>

        <ConversationEmptyState>
          <div className="flex flex-col items-center justify-center h-full gap-4">
            <h1 className="text-2xl font-bold">Welcome to Chat</h1>
            <p className="text-gray-500">Start a conversation below</p>
            
            {/* Suggestions for empty state */}
            <div className="flex gap-2 flex-wrap justify-center">
              <Suggestion
                text="Explain quantum computing"
                onClick={() => sendMessage({ text: 'Explain quantum computing' })}
              />
              <Suggestion
                text="Write a poem"
                onClick={() => sendMessage({ text: 'Write a poem' })}
              />
              <Suggestion
                text="Help with code"
                onClick={() => sendMessage({ text: 'Help me with this code' })}
              />
            </div>
          </div>
        </ConversationEmptyState>
      </Conversation>

      {/* Error state */}
      {error && (
        <div className="p-4 bg-red-50 border-t border-red-200">
          <div className="flex justify-between items-center">
            <span className="text-red-900">Something went wrong</span>
            <div className="flex gap-2">
              <button
                onClick={reload}
                className="px-3 py-1 bg-red-600 text-white rounded text-sm"
              >
                Retry
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Input area */}
      <div className="border-t p-4">
        <PromptInput
          onSend={(text, attachments) => {
            sendMessage({
              text,
              files: attachments,
            });
          }}
          disabled={status !== 'ready'}
          placeholder="Ask me anything..."
        />
      </div>
    </div>
  );
}
```

### File Upload with Attachments

```typescript
'use client';

import { useChat } from '@ai-sdk/react';
import { PromptInput } from '@/components/ai-elements/prompt-input';
import { Attachment } from '@/components/ai-elements/attachment';

export default function ChatWithFiles() {
  const { messages, sendMessage, status } = useChat({
    api: '/api/chat',
  });

  return (
    <div>
      {/* Display attachments from messages */}
      {messages.map(msg => (
        <div key={msg.id}>
          {msg.parts.map((part, idx) => {
            if (part.type === 'file') {
              return (
                <Attachment
                  key={idx}
                  filename={part.filename}
                  mediaType={part.mediaType}
                  url={part.url}
                  onDelete={() => {
                    // Handle file deletion
                  }}
                />
              );
            }
            return null;
          })}
        </div>
      ))}

      {/* Input with file support */}
      <PromptInput
        onSend={(text, files) => {
          sendMessage({
            text,
            files: files,
          });
        }}
        disabled={status !== 'ready'}
        attachmentTypes="image/*,text/*,.pdf"
      />
    </div>
  );
}
```

---

## Backend Implementation

### Basic Server Handler

```typescript
// app/api/chat/route.ts
import { streamText } from 'ai';
import { openai } from '@ai-sdk/openai';

export const maxDuration = 30;

export async function POST(req: Request) {
  const { messages } = await req.json();

  const result = streamText({
    model: openai('gpt-4o-mini'),
    system: 'You are a helpful assistant.',
    messages,
  });

  return result.toDataStreamResponse();
}
```

### With Tool Integration

```typescript
import { streamText, tool } from 'ai';
import { openai } from '@ai-sdk/openai';
import { z } from 'zod';

export async function POST(req: Request) {
  const { messages } = await req.json();

  const result = streamText({
    model: openai('gpt-4o'),
    system: 'You are a helpful assistant with access to tools.',
    messages,
    tools: {
      weather: tool({
        description: 'Get weather for a city',
        parameters: z.object({
          city: z.string(),
          units: z.enum(['celsius', 'fahrenheit']).default('celsius'),
        }),
        execute: async ({ city, units }) => {
          const response = await fetch(
            `https://api.weatherapi.com/v1/current.json?q=${city}`,
            { headers: { key: process.env.WEATHER_API_KEY } }
          );
          const data = await response.json();
          return units === 'celsius'
            ? `${data.current.temp_c}°C in ${city}`
            : `${data.current.temp_f}°F in ${city}`;
        },
      }),
      
      search: tool({
        description: 'Search the web',
        parameters: z.object({
          query: z.string(),
        }),
        execute: async ({ query }) => {
          // Implement your search logic
          return `Search results for: ${query}`;
        },
      }),
    },
  });

  return result.toDataStreamResponse();
}
```

---

## Tool Integration

### Client-Side Tool Handling

```typescript
'use client';

import { useChat } from '@ai-sdk/react';
import { Conversation } from '@/components/ai-elements/conversation';
import { Message } from '@/components/ai-elements/message';
import { Tool } from '@/components/ai-elements/tool';

export default function ChatWithTools() {
  const { messages, sendMessage, addToolOutput, status } = useChat({
    api: '/api/chat',
    onToolCall: async ({ toolCall }) => {
      // Handle client-side tool calls if needed
      if (toolCall.toolName === 'getUserLocation') {
        navigator.geolocation.getCurrentPosition(position => {
          addToolOutput({
            tool: 'getUserLocation',
            toolCallId: toolCall.toolCallId,
            output: {
              lat: position.coords.latitude,
              lng: position.coords.longitude,
            },
          });
        });
      }
    },
  });

  return (
    <Conversation>
      {messages.map(message => (
        <Message key={message.id} role={message.role}>
          {message.parts.map((part, idx) => {
            if (part.type?.startsWith('tool-')) {
              return (
                <Tool
                  key={idx}
                  name={part.type.replace('tool-', '')}
                  status={
                    part.state === 'input-streaming' ? 'running' :
                    part.state === 'output-available' ? 'success' : 'running'
                  }
                  input={part.input}
                  output={part.output}
                />
              );
            }
            return null;
          })}
        </Message>
      ))}
    </Conversation>
  );
}
```

---

## Advanced Patterns

### Message Persistence

```typescript
'use client';

import { useChat } from '@ai-sdk/react';
import { useEffect, useState } from 'react';
import type { UIMessage } from 'ai';

const STORAGE_KEY = 'chat_messages';

export default function PersistentChat() {
  const [isMounted, setIsMounted] = useState(false);
  const { messages, setMessages, sendMessage } = useChat({
    api: '/api/chat',
  });

  // Load from storage
  useEffect(() => {
    setIsMounted(true);
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      try {
        setMessages(JSON.parse(stored) as UIMessage[]);
      } catch (err) {
        console.error('Failed to load messages:', err);
      }
    }
  }, [setMessages]);

  // Save to storage
  useEffect(() => {
    if (isMounted && messages.length > 0) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(messages));
    }
  }, [messages, isMounted]);

  const clearHistory = () => {
    setMessages([]);
    localStorage.removeItem(STORAGE_KEY);
  };

  if (!isMounted) return <div>Loading...</div>;

  return (
    <div>
      {/* Chat UI */}
      <button onClick={clearHistory} className="text-sm text-red-600">
        Clear History
      </button>
    </div>
  );
}
```

### Branching Conversations

```typescript
'use client';

import { useChat } from '@ai-sdk/react';
import { Branch } from '@/components/ai-elements/branch';
import { Message } from '@/components/ai-elements/message';

export default function BranchingChat() {
  const { messages, sendMessage } = useChat({
    api: '/api/chat',
  });

  const groupedMessages = messages.reduce((acc, msg) => {
    const parentId = (msg.metadata as any)?.parentId || 'main';
    if (!acc[parentId]) acc[parentId] = [];
    acc[parentId].push(msg);
    return acc;
  }, {} as Record<string, any[]>);

  return (
    <div>
      {Object.entries(groupedMessages).map(([branchId, branchMessages]) => (
        <Branch
          key={branchId}
          id={branchId}
          label={branchId === 'main' ? 'Main' : `Branch ${branchId}`}
          isActive={branchId === 'main'}
        >
          {branchMessages.map(msg => (
            <Message key={msg.id} role={msg.role}>
              {/* Message content */}
            </Message>
          ))}
        </Branch>
      ))}
    </div>
  );
}
```

---

## Error Handling

### Comprehensive Error Management

```typescript
'use client';

import { useChat } from '@ai-sdk/react';
import { useState } from 'react';

export default function RobustChat() {
  const [errorDetails, setErrorDetails] = useState('');
  
  const { messages, sendMessage, error, reload, status } = useChat({
    api: '/api/chat',
    onError: (error: Error) => {
      console.error('Chat error:', error);
      setErrorDetails(error.message);
      
      // Optional: Report to error tracking service
      // reportToSentry(error);
    },
  });

  if (error) {
    return (
      <div className="p-4 bg-red-50 border border-red-200 rounded">
        <h3 className="font-semibold text-red-900">Error Occurred</h3>
        <p className="text-red-700 text-sm mt-2">
          Something went wrong. Please try again.
        </p>
        {process.env.NODE_ENV === 'development' && (
          <details className="mt-2">
            <summary className="text-red-600 text-xs cursor-pointer">
              Details
            </summary>
            <pre className="mt-2 bg-red-100 p-2 text-xs overflow-auto">
              {errorDetails}
            </pre>
          </details>
        )}
        <button
          onClick={reload}
          className="mt-3 px-3 py-1 bg-red-600 text-white rounded text-sm"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div>
      {/* Chat content */}
    </div>
  );
}
```

---

## Performance Optimization

### Throttling Updates

```typescript
const { messages } = useChat({
  api: '/api/chat',
  experimental_throttle: 50, // Throttle UI updates to 50ms
});
```

### Lazy Loading Long Conversations

```typescript
const [displayedCount, setDisplayedCount] = useState(20);

return (
  <div>
    {displayedCount < messages.length && (
      <button
        onClick={() => setDisplayedCount(prev => prev + 20)}
        className="text-sm text-blue-600"
      >
        Load earlier messages
      </button>
    )}
    {messages.slice(-displayedCount).map(msg => (
      <Message key={msg.id} role={msg.role}>
        {/* Content */}
      </Message>
    ))}
  </div>
);
```

---

## Type Safety

### Custom Message Types

```typescript
// types/chat.ts
import type { UIMessage } from 'ai';

export interface ChatMetadata {
  userId?: string;
  sessionId?: string;
  createdAt: number;
  tokens?: number;
}

export type CustomMessage = UIMessage<ChatMetadata>;
```

### Typed useChat

```typescript
import type { CustomMessage } from '@/types/chat';

const { messages } = useChat<CustomMessage>({
  api: '/api/chat',
  onFinish: ({ message }) => {
    // Type-safe metadata access
    console.log('User:', message.metadata?.userId);
    console.log('Tokens:', message.metadata?.tokens);
  },
});
```

---

## Migration from AI SDK v4 → v5

### Key Changes

| Aspect | v4 | v5 |
|--------|----|----|
| Input management | Auto-managed by hook | Manual control |
| Message format | `content: string` | `parts[]` array |
| Transport | Built-in | Pluggable |
| Tool handling | Implicit | Explicit callbacks |
| Components | None | 20+ AI Elements |

### Migration Example

**v4:**
```typescript
const { input, setInput, handleInputChange, messages } = useChat();
<input value={input} onChange={handleInputChange} />
```

**v5:**
```typescript
const { messages, sendMessage } = useChat();
const [input, setInput] = useState('');
<PromptInput onSend={text => sendMessage({ text })} />
```

---

## Production Checklist

### AI Elements Setup
- [ ] Install all required components
- [ ] Configure shadcn/ui colors to match brand
- [ ] Set up AI Gateway for cost savings (optional)
- [ ] Test responsive design on mobile

### Chat Features
- [ ] Implement error handling and retry logic
- [ ] Add message persistence (localStorage/database)
- [ ] Set up typing indicators for long responses
- [ ] Add attachment support if needed
- [ ] Implement suggestion pills for empty state

### Backend
- [ ] Secure API endpoints with authentication
- [ ] Set `maxDuration` on server route (30-60s)
- [ ] Implement rate limiting
- [ ] Log conversations for analytics (privacy-aware)
- [ ] Monitor token usage and costs

### Monitoring & UX
- [ ] Set up error reporting (Sentry, etc.)
- [ ] Monitor performance metrics
- [ ] Test with large conversation histories
- [ ] Verify accessibility (keyboard nav, screen readers)
- [ ] Set up analytics for user engagement

---

## Resources

- **AI SDK Docs**: https://ai-sdk.dev
- **AI Elements Docs**: https://ai-sdk.dev/elements
- **GitHub**: https://github.com/vercel/ai
- **shadcn/ui**: https://ui.shadcn.com
- **Vercel Academy**: https://vercel.com/academy

---

## Quick Reference

### Installation Commands

```bash
# All components
npx ai-elements@latest

# Core chat only
npx ai-elements@latest add conversation message response prompt-input actions

# Extended features
npx ai-elements@latest add suggestion reasoning tool branch attachment sources

# Via shadcn/ui
npx shadcn@latest add https://registry.ai-sdk.dev/all.json
```

### Import Patterns

```typescript
import { Conversation, ConversationContent, ConversationEmptyState } from '@/components/ai-elements/conversation';
import { Message } from '@/components/ai-elements/message';
import { Response } from '@/components/ai-elements/response';
import { PromptInput } from '@/components/ai-elements/prompt-input';
import { Actions } from '@/components/ai-elements/actions';
import { Suggestion } from '@/components/ai-elements/suggestion';
import { Tool } from '@/components/ai-elements/tool';
import { Reasoning } from '@/components/ai-elements/reasoning';
import { Sources } from '@/components/ai-elements/sources';
import { Branch } from '@/components/ai-elements/branch';
import { Attachment } from '@/components/ai-elements/attachment';
import { Citation } from '@/components/ai-elements/citation';
```

### Core Imports from AI SDK

```typescript
import { useChat } from '@ai-sdk/react';
import { streamText, tool } from 'ai';
import { openai } from '@ai-sdk/openai';
import { anthropic } from '@ai-sdk/anthropic';
```

---

**Last Updated:** December 2025 | AI SDK v5.0+ | AI Elements 2025