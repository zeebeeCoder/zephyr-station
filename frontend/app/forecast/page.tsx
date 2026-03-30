'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import type { ForecastDay } from '@/lib/tools/forecast';

export default function ForecastPage() {
  const [forecast, setForecast] = useState<ForecastDay[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch('/api/forecast')
      .then((res) => {
        if (!res.ok) throw new Error('Failed to fetch forecast');
        return res.json();
      })
      .then((data) => {
        setForecast(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, []);

  return (
    <main className="min-h-screen max-w-5xl mx-auto p-4 md:p-8">
      <header className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold flex items-center gap-2">
            <span>🔮</span>
            <span>7-Day Forecast</span>
          </h1>
          <p className="text-sm text-muted-foreground">
            Jelenia Gora, Poland
          </p>
        </div>
        <Link
          href="/"
          className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors px-3 py-1.5 rounded-md border border-border hover:bg-muted"
        >
          🌤️ Back to Chat
        </Link>
      </header>

      {loading && (
        <div className="flex items-center justify-center py-20">
          <p className="text-muted-foreground">Loading forecast...</p>
        </div>
      )}

      {error && (
        <div className="flex items-center justify-center py-20">
          <p className="text-destructive">Error: {error}</p>
        </div>
      )}

      {!loading && !error && (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-7 gap-4">
          {forecast.map((day) => (
            <Card key={day.date} className="text-center">
              <CardHeader className="pb-2 px-3 pt-4">
                <CardTitle className="text-base">{day.dayName}</CardTitle>
                <p className="text-xs text-muted-foreground">{day.date}</p>
              </CardHeader>
              <CardContent className="px-3 pb-4 space-y-3">
                <div className="text-4xl">{day.conditionEmoji}</div>
                <p className="text-sm text-muted-foreground">{day.condition}</p>
                <div className="space-y-1">
                  <p className="text-2xl font-semibold">{day.tempMax}°</p>
                  <p className="text-sm text-muted-foreground">{day.tempMin}°</p>
                </div>
                <div className="pt-2 border-t">
                  <div className="flex items-center justify-center gap-1 text-sm">
                    <span>💧</span>
                    <span className={day.precipChance > 50 ? 'font-semibold' : 'text-muted-foreground'}>
                      {day.precipChance}%
                    </span>
                  </div>
                  <div className="mt-1 h-1.5 rounded-full bg-muted overflow-hidden">
                    <div
                      className="h-full rounded-full bg-blue-500 transition-all"
                      style={{ width: `${day.precipChance}%` }}
                    />
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <footer className="mt-8 text-center text-xs text-muted-foreground">
        Data from Open-Meteo.com | Updates every 30 minutes
      </footer>
    </main>
  );
}
