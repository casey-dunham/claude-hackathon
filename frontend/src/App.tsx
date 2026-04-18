import { useEffect, useState } from 'react';
import ChatPanel from './components/ChatPanel';
import FoodMap from './components/FoodMap';
import { getChatHistory, getHealth, getLog, getNearbyPlaces } from './services/api';
import { ChatMessage, FoodEntry, NearbyPlace } from './services/types';

const DEFAULT_LAT = 40.7549;
const DEFAULT_LNG = -73.984;

function sortEntries(entries: FoodEntry[]): FoodEntry[] {
  return [...entries].sort(
    (a, b) => new Date(b.logged_at).getTime() - new Date(a.logged_at).getTime()
  );
}

function formatDateTime(isoValue: string): string {
  return new Date(isoValue).toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  });
}

function errorMessage(error: unknown): string {
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return 'Unable to load data from backend.';
}

function mealWindowForHour(hour: number): 'breakfast' | 'lunch' | 'afternoon snack' | 'dinner' | 'late night' {
  if (hour >= 5 && hour < 11) return 'breakfast';
  if (hour >= 11 && hour < 15) return 'lunch';
  if (hour >= 15 && hour < 17) return 'afternoon snack';
  if (hour >= 17 && hour < 22) return 'dinner';
  return 'late night';
}

function recommendationScore(place: NearbyPlace): number {
  const openScore = place.is_open === true ? 30 : place.is_open === false ? -20 : 0;
  const ratingScore = (place.rating ?? 3.5) * 10;
  const distancePenalty = Math.min(place.distance_m, 2500) / 100;
  return openScore + ratingScore - distancePenalty;
}

function LogSourceIcon({ source }: { source: FoodEntry['source'] }) {
  if (source === 'chat') {
    return (
      <svg viewBox="0 0 24 24" className="h-3.5 w-3.5 text-[#2563eb]" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M21 11.5a8.5 8.5 0 1 1-4.2-7.4" />
        <path d="M21 4v6h-6" />
      </svg>
    );
  }

  return (
    <svg viewBox="0 0 24 24" className="h-3.5 w-3.5 text-[#16a34a]" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M12 20h9" />
      <path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4z" />
    </svg>
  );
}

export default function App() {
  const [userLat, setUserLat] = useState(DEFAULT_LAT);
  const [userLng, setUserLng] = useState(DEFAULT_LNG);
  const [places, setPlaces] = useState<NearbyPlace[]>([]);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [entries, setEntries] = useState<FoodEntry[]>([]);
  const [backendOnline, setBackendOnline] = useState(false);
  const [isPlacesLoading, setIsPlacesLoading] = useState(false);
  const [placesError, setPlacesError] = useState<string | null>(null);
  const [isLogLoading, setIsLogLoading] = useState(true);
  const [logError, setLogError] = useState<string | null>(null);
  const [locationStatus, setLocationStatus] = useState<'loading' | 'granted' | 'denied'>('loading');
  const userTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC';
  const currentMealWindow = mealWindowForHour(new Date().getHours());
  const recommendedPlaces = [...places]
    .sort((a, b) => recommendationScore(b) - recommendationScore(a))
    .slice(0, 4);

  async function refreshLog() {
    const response = await getLog();
    setEntries(sortEntries(response.entries));
  }

  async function refreshNearbyPlaces(lat: number, lng: number) {
    setIsPlacesLoading(true);
    setPlacesError(null);
    try {
      const response = await getNearbyPlaces(lat, lng);
      setPlaces(response.places);
    } catch (error) {
      setPlacesError(errorMessage(error));
      setPlaces([]);
    } finally {
      setIsPlacesLoading(false);
    }
  }

  useEffect(() => {
    if (!navigator.geolocation) {
      setLocationStatus('denied');
      return;
    }

    navigator.geolocation.getCurrentPosition(
      (position) => {
        const lat = position.coords.latitude;
        const lng = position.coords.longitude;
        setUserLat(lat);
        setUserLng(lng);
        setLocationStatus('granted');
      },
      () => {
        setLocationStatus('denied');
      },
      { enableHighAccuracy: true, timeout: 8000 }
    );
  }, []);

  useEffect(() => {
    void refreshNearbyPlaces(userLat, userLng);
  }, [userLat, userLng]);

  useEffect(() => {
    let mounted = true;

    async function init() {
      setIsLogLoading(true);
      setLogError(null);

      try {
        await getHealth();
      } catch (error) {
        if (!mounted) return;
        setBackendOnline(false);
        setLogError(errorMessage(error));
        setIsLogLoading(false);
        return;
      }

      if (!mounted) return;
      setBackendOnline(true);

      const [historyResult, logResult] = await Promise.allSettled([getChatHistory(), getLog()]);

      if (!mounted) return;

      if (historyResult.status === 'fulfilled') {
        setChatMessages(historyResult.value.messages);
      }

      if (logResult.status === 'fulfilled') {
        setEntries(sortEntries(logResult.value.entries));
      } else {
        setLogError(errorMessage(logResult.reason));
      }

      setIsLogLoading(false);
    }

    void init();

    return () => {
      mounted = false;
    };
  }, []);

  function handleNewMessage(userMsg: ChatMessage, assistantMsg: ChatMessage) {
    setChatMessages((prev) => [...prev, userMsg, assistantMsg]);
    void refreshLog().then(
      () => setLogError(null),
      (error) => setLogError(errorMessage(error))
    );
  }

  return (
    <div className="min-h-screen bg-[#fafafa]">
      <header className="border-b border-[#f0f0f0] bg-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <div className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-[#18181b] text-sm font-semibold text-white">
              N
            </div>
            <span className="text-base font-semibold tracking-tight text-[#18181b]">NutriCoach MVP</span>
          </div>
          <div className="flex items-center gap-1.5">
            <div className={`h-1.5 w-1.5 rounded-full ${backendOnline ? 'bg-green-500' : 'bg-[#d4d4d8]'}`} />
            <span className="text-xs text-[#a1a1aa]">{backendOnline ? 'Connected' : 'Backend offline'}</span>
          </div>
        </div>
      </header>

      <main className="mx-auto grid max-w-6xl grid-cols-1 gap-6 px-6 py-6 lg:grid-cols-5">
        <section className="lg:col-span-5">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-medium text-[#18181b]">Nearby Healthy Food</h2>
            <div className="flex items-center gap-2 text-xs text-[#a1a1aa]">
              {locationStatus === 'denied' && <span>Using default location</span>}
              <span>{isPlacesLoading ? 'Loading places...' : `${places.length} places`}</span>
            </div>
          </div>
          <FoodMap userLat={userLat} userLng={userLng} places={places} />
          {placesError && <p className="mt-2 text-xs text-[#b91c1c]">{placesError}</p>}
        </section>

        <section className="lg:col-span-2">
          <h2 className="mb-3 text-sm font-medium text-[#18181b]">Ask the Coach</h2>
          <ChatPanel
            messages={chatMessages}
            onNewMessage={handleNewMessage}
            backendOnline={backendOnline}
            chatContext={{
              lat: userLat,
              lng: userLng,
              timezone: userTimezone,
            }}
          />
          <p className="mt-2 text-xs text-[#a1a1aa]">
            Try: Recommend a high-protein {currentMealWindow} near me, or type "delete last"
          </p>
        </section>

        <section className="rounded-xl border border-[#f0f0f0] bg-white p-5 lg:col-span-3">
          <h2 className="mb-3 text-sm font-medium text-[#18181b]">Today&apos;s Log</h2>

          {isLogLoading && entries.length === 0 ? (
            <p className="text-sm text-[#a1a1aa]">Loading data from backend...</p>
          ) : entries.length === 0 ? (
            <p className="text-sm text-[#a1a1aa]">No entries logged today.</p>
          ) : (
            <div className="space-y-2">
              {entries.map((entry) => (
                <div
                  key={entry.id}
                  className="rounded-lg border border-[#f0f0f0] bg-[#fafafa] px-4 py-3"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-start gap-2.5">
                      <div className="mt-0.5 rounded-md bg-white p-1.5 ring-1 ring-[#e4e4e7]">
                        <LogSourceIcon source={entry.source} />
                      </div>
                      <div>
                        <p className="text-sm font-medium text-[#18181b]">{entry.name}</p>
                        <p className="mt-0.5 text-xs text-[#a1a1aa]">
                          {formatDateTime(entry.logged_at)} · {entry.source}
                        </p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="text-sm font-medium text-[#18181b]">{entry.calories} kcal</p>
                      <p className="mt-0.5 text-xs text-[#a1a1aa]">
                        P {entry.protein_g}g · C {entry.carbs_g}g · F {entry.fat_g}g
                      </p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {logError && <p className="mt-3 text-xs text-[#b91c1c]">{logError}</p>}
        </section>

        <section className="rounded-xl border border-[#f0f0f0] bg-white p-5 lg:col-span-5">
          <h2 className="mb-3 text-sm font-medium text-[#18181b]">
            Recommended for {currentMealWindow}
          </h2>
          {recommendedPlaces.length === 0 ? (
            <p className="text-sm text-[#a1a1aa]">No places found.</p>
          ) : (
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
              {recommendedPlaces.map((place) => (
                <a
                  key={place.id}
                  href={place.maps_url}
                  target="_blank"
                  rel="noreferrer"
                  className="rounded-lg border border-[#f0f0f0] bg-[#fafafa] px-3 py-2 hover:border-[#d4d4d8]"
                >
                  <p className="text-sm font-medium text-[#18181b]">{place.name}</p>
                  <p className="mt-0.5 text-xs text-[#a1a1aa]">{place.address}</p>
                  <p className="mt-1 text-xs text-[#71717a]">
                    {place.distance_m}m away
                    {place.rating !== null ? ` · ${place.rating.toFixed(1)}★` : ''}
                    {place.is_open === true ? ' · Open now' : ''}
                    {place.is_open === false ? ' · Closed now' : ''}
                  </p>
                </a>
              ))}
            </div>
          )}
        </section>
      </main>
    </div>
  );
}
