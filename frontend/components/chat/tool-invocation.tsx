'use client';

import type { ReactNode } from 'react';
import { cn } from '@/lib/utils';

interface ToolInvocationProps {
  toolName: string;
  state: 'input-streaming' | 'input-available' | 'output-available' | 'output-error';
  input?: unknown;
  output?: unknown;
  errorText?: string;
}

// Weather-specific icons and formatting
const TOOL_CONFIG: Record<string, { icon: string; label: string }> = {
  get_current: { icon: '🌡️', label: 'Current Reading' },
  query_range: { icon: '📊', label: 'Time Range Query' },
  compare_periods: { icon: '📈', label: 'Period Comparison' },
  execute_sql: { icon: '🔍', label: 'Database Query' },
};

function formatOutput(toolName: string, output: unknown): ReactNode {
  if (!output) return null;

  // For weather readings, show a nice table
  if (toolName === 'get_current' && Array.isArray(output)) {
    const reading = output[0];
    if (!reading) return <span className="text-muted-foreground">No readings available</span>;

    return (
      <div className="grid grid-cols-2 gap-2 text-sm">
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
      <div className="text-sm space-y-1">
        <div>Period 1: {data.period1?.avg_temperature?.toFixed(1)}°C avg</div>
        <div>Period 2: {data.period2?.avg_temperature?.toFixed(1)}°C avg</div>
      </div>
    );
  }

  // Default: show JSON
  return (
    <pre className="text-xs overflow-x-auto max-h-32">
      {JSON.stringify(output, null, 2)}
    </pre>
  );
}

export function ToolInvocation({ toolName, state, input, output, errorText }: ToolInvocationProps) {
  const config = TOOL_CONFIG[toolName] || { icon: '🔧', label: toolName };

  return (
    <div
      className={cn(
        'rounded-md border p-3 text-sm my-2',
        state === 'input-streaming' && 'bg-muted/50 border-muted animate-pulse',
        state === 'input-available' && 'bg-muted/50 border-muted',
        state === 'output-available' && 'bg-primary/5 border-primary/20',
        state === 'output-error' && 'bg-destructive/10 border-destructive/20'
      )}
    >
      <div className="flex items-center gap-2 font-medium mb-2">
        <span>{config.icon}</span>
        <span>{config.label}</span>
        {state === 'input-streaming' && (
          <span className="text-muted-foreground text-xs">(loading...)</span>
        )}
      </div>

      {state === 'output-available' && output !== undefined && (
        <div className="mt-2">{formatOutput(toolName, output)}</div>
      )}

      {state === 'output-error' && errorText && (
        <div className="text-destructive text-xs mt-1">Error: {errorText}</div>
      )}
    </div>
  );
}
