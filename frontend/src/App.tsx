import { useEffect, useState } from 'react';
type Tab = 'log' | 'dashboard' | 'map' | 'profile';
import ChatPanel from './components/ChatPanel';
import DashboardTab from './components/DashboardTab';
import FoodMap from './components/FoodMap';
import ProfileTab from './components/ProfileTab';
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

export default function App() {
  const [activeTab, setActiveTab] = useState<Tab>('log');
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

      <div className="mx-auto max-w-6xl px-6 pt-4">
        <div className="flex gap-1 border-b border-[#f0f0f0]">
          {(['log', 'dashboard', 'map', 'profile'] as Tab[]).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-2 text-sm font-medium transition-colors ${
                activeTab === tab
                  ? 'border-b-2 border-[#18181b] text-[#18181b]'
                  : 'text-[#a1a1aa] hover:text-[#71717a]'
              }`}
            >
              {tab === 'log' ? 'Chat & Log' : tab === 'dashboard' ? 'Dashboard' : tab === 'map' ? 'Nearby Food' : 'Profile'}
            </button>
          ))}
        </div>
      </div>

      <main className="mx-auto max-w-6xl px-6 py-6">
        {activeTab === 'log' && (
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-5">
            <section className="lg:col-span-2">
              <h2 className="mb-3 text-sm font-medium text-[#18181b]">Ask the Coach</h2>
              <ChatPanel
                messages={chatMessages}
                onNewMessage={handleNewMessage}
                backendOnline={backendOnline}
                userLat={userLat}
                userLng={userLng}
              />
              <p className="mt-2 text-xs text-[#a1a1aa]">
                Try: log greek yogurt 150 cal 15p 12c 4f
              </p>
            </section>

            <section className="rounded-xl border border-[#f0f0f0] bg-white p-5 lg:col-span-3">
              <h2 className="mb-3 text-sm font-medium text-[#18181b]">Today&apos;s Log</h2>

              {isLogLoading && entries.length === 0 ? (
                <p className="text-sm text-[#a1a1aa]">Loading data from backend...</p>
              ) : entries.length === 0 ? (
                <p className="text-sm text-[#a1a1aa]">No entries logged today.</p>
              ) : (
                <div className="max-h-96 overflow-y-auto space-y-2 pr-1">
                  {entries.map((entry) => (
                    <div
                      key={entry.id}
                      className="rounded-lg border border-[#f0f0f0] bg-[#fafafa] px-4 py-3"
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <p className="text-sm font-medium text-[#18181b]">{entry.name}</p>
                          <p className="mt-0.5 text-xs text-[#a1a1aa]">
                            {formatDateTime(entry.logged_at)} · {entry.source}
                          </p>
                        </div>
                        <p className="text-sm font-medium text-[#18181b]">{entry.calories} kcal</p>
                      </div>
                      <p className="mt-2 text-xs text-[#71717a]">
                        P {entry.protein_g}g · C {entry.carbs_g}g · F {entry.fat_g}g
                      </p>
                    </div>
                  ))}
                </div>
              )}

              {logError && <p className="mt-3 text-xs text-[#b91c1c]">{logError}</p>}
            </section>
          </div>
        )}

        {activeTab === 'dashboard' && <DashboardTab />}

        {activeTab === 'profile' && <ProfileTab />}

        {activeTab === 'map' && (
          <div className="space-y-6">
            <section>
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

            <section className="rounded-xl border border-[#f0f0f0] bg-white p-5">
              <h2 className="mb-3 text-sm font-medium text-[#18181b]">Nearby Places</h2>
              {places.length === 0 ? (
                <p className="text-sm text-[#a1a1aa]">No places found.</p>
              ) : (
                <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
                  {places.map((place) => (
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
          </div>
        )}
      </main>
    </div>
  );
}
