import { streamText, convertToModelMessages, UIMessage, stepCountIs } from 'ai';
import { openai } from '@ai-sdk/openai';
import { weatherTools } from '@/lib/tools/weather';
import { getSystemPrompt } from '@/lib/prompts/system';
import { getDbClient } from '@/lib/db/client';

export const maxDuration = 30;

async function getContext() {
  const db = getDbClient();

  // Get available devices
  const devices = await db.query<{ id: string }>('SELECT id FROM devices WHERE is_active = true');
  const deviceIds = devices.map(d => d.id);

  // Get data range
  const range = await db.query<{ min_time: string; max_time: string }>(`
    SELECT MIN(recorded_at) as min_time, MAX(recorded_at) as max_time FROM readings
  `);

  const dataRange = range[0]?.min_time && range[0]?.max_time
    ? `${new Date(range[0].min_time).toLocaleDateString()} to ${new Date(range[0].max_time).toLocaleDateString()}`
    : 'No data available';

  return {
    currentTime: new Date().toISOString(),
    devices: deviceIds.length > 0 ? deviceIds : ['station-01'],
    dataRange,
  };
}

export async function POST(req: Request) {
  try {
    const { messages }: { messages: UIMessage[] } = await req.json();

    // Get dynamic context
    const context = await getContext();

    const result = streamText({
      model: openai('gpt-4o'),
      system: getSystemPrompt(context),
      messages: convertToModelMessages(messages),
      tools: weatherTools,
      stopWhen: stepCountIs(5), // Allow up to 5 steps for multi-tool usage
    });

    return result.toUIMessageStreamResponse();
  } catch (error) {
    console.error('Chat API error:', error);
    return new Response(
      JSON.stringify({ error: 'Failed to process chat request' }),
      { status: 500, headers: { 'Content-Type': 'application/json' } }
    );
  }
}
