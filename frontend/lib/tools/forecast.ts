import { tool } from 'ai';
import { z } from 'zod';

// ============================================================================
// Types
// ============================================================================

export interface ForecastDay {
  date: string;
  dayName: string;
  tempMax: number;
  tempMin: number;
  precipChance: number;
  weatherCode: number;
  condition: string;
  conditionEmoji: string;
}

// ============================================================================
// WMO Weather Code Mapping
// ============================================================================

function wmoCodeToCondition(code: number): { text: string; emoji: string } {
  if (code === 0) return { text: 'Clear sky', emoji: '☀️' };
  if (code === 1) return { text: 'Mainly clear', emoji: '🌤️' };
  if (code === 2) return { text: 'Partly cloudy', emoji: '⛅' };
  if (code === 3) return { text: 'Overcast', emoji: '☁️' };
  if (code === 45 || code === 48) return { text: 'Fog', emoji: '🌫️' };
  if (code >= 51 && code <= 55) return { text: 'Drizzle', emoji: '🌦️' };
  if (code >= 56 && code <= 57) return { text: 'Freezing drizzle', emoji: '🌧️' };
  if (code >= 61 && code <= 63) return { text: 'Rain', emoji: '🌧️' };
  if (code === 65) return { text: 'Heavy rain', emoji: '🌧️' };
  if (code >= 66 && code <= 67) return { text: 'Freezing rain', emoji: '🧊' };
  if (code >= 71 && code <= 75) return { text: 'Snow', emoji: '🌨️' };
  if (code === 77) return { text: 'Snow grains', emoji: '🌨️' };
  if (code >= 80 && code <= 82) return { text: 'Rain showers', emoji: '🌦️' };
  if (code >= 85 && code <= 86) return { text: 'Snow showers', emoji: '🌨️' };
  if (code === 95) return { text: 'Thunderstorm', emoji: '⛈️' };
  if (code >= 96 && code <= 99) return { text: 'Thunderstorm with hail', emoji: '⛈️' };
  return { text: 'Unknown', emoji: '❓' };
}

function getDayName(dateStr: string): string {
  const date = new Date(dateStr + 'T12:00:00');
  return date.toLocaleDateString('en-US', { weekday: 'long' });
}

// ============================================================================
// Shared Fetch Helper
// ============================================================================

export async function fetchOpenMeteoForecast(days: number = 3): Promise<ForecastDay[]> {
  const url = `https://api.open-meteo.com/v1/forecast?latitude=50.90&longitude=15.73&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max,weathercode&timezone=Europe%2FWarsaw&forecast_days=${days}`;

  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Open-Meteo API error: ${response.status}`);
  }

  const data = await response.json();
  const daily = data.daily;

  const result: ForecastDay[] = [];
  for (let i = 0; i < daily.time.length; i++) {
    const condition = wmoCodeToCondition(daily.weathercode[i]);
    result.push({
      date: daily.time[i],
      dayName: getDayName(daily.time[i]),
      tempMax: daily.temperature_2m_max[i],
      tempMin: daily.temperature_2m_min[i],
      precipChance: daily.precipitation_probability_max[i],
      weatherCode: daily.weathercode[i],
      condition: condition.text,
      conditionEmoji: condition.emoji,
    });
  }

  return result;
}

// ============================================================================
// AI Tool: Get Forecast
// ============================================================================

const getForecastSchema = z.object({
  days: z.number().optional().default(3).describe('Number of forecast days (1-7, default 3)'),
});

export const getForecast = tool({
  description: 'Get the weather forecast for Jelenia Gora, Poland. Returns daily high/low temperature, weather condition, and rain probability.',
  inputSchema: getForecastSchema,
  execute: async ({ days }): Promise<ForecastDay[]> => {
    return fetchOpenMeteoForecast(Math.min(Math.max(days, 1), 7));
  },
});
