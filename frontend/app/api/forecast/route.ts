import { fetchOpenMeteoForecast } from '@/lib/tools/forecast';
import { NextResponse } from 'next/server';

export const revalidate = 1800; // Cache for 30 minutes

export async function GET() {
  try {
    const forecast = await fetchOpenMeteoForecast(7);
    return NextResponse.json(forecast, {
      headers: { 'Cache-Control': 'public, s-maxage=1800, stale-while-revalidate=3600' },
    });
  } catch (error) {
    console.error('Forecast API error:', error);
    return NextResponse.json(
      { error: 'Failed to fetch forecast' },
      { status: 500 }
    );
  }
}
