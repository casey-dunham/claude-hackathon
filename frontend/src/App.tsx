import { useState, useEffect } from 'react';
import FoodMap from './components/FoodMap';
import RecommendationCard from './components/RecommendationCard';
import ChatPanel from './components/ChatPanel';
import { NearbyPlace, Recommendation, ChatMessage } from './services/types';
import { getNearbyPlaces } from './services/mock/places';
import { getRecommendations } from './services/mock/recommendations';
import { checkHealth, getChatHistory } from './services/api';

// Default location (midtown Manhattan)
const DEFAULT_LAT = 40.7549;
const DEFAULT_LNG = -73.984;

export default function App() {
  const [userLat, setUserLat] = useState(DEFAULT_LAT);
  const [userLng, setUserLng] = useState(DEFAULT_LNG);
  const [places, setPlaces] = useState<NearbyPlace[]>([]);
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [backendOnline, setBackendOnline] = useState(false);
  const [locationStatus, setLocationStatus] = useState<'loading' | 'granted' | 'denied'>('loading');

  // Get user location
  useEffect(() => {
    if (!navigator.geolocation) {
      setLocationStatus('denied');
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setUserLat(pos.coords.latitude);
        setUserLng(pos.coords.longitude);
        setLocationStatus('granted');
      },
      () => {
        setLocationStatus('denied');
      }
    );
  }, []);

  // Load mock data when location is set
  useEffect(() => {
    async function loadData() {
      const [p, r] = await Promise.all([
        getNearbyPlaces(userLat, userLng),
        getRecommendations(userLat, userLng),
      ]);
      setPlaces(p);
      setRecommendations(r);
    }
    loadData();
  }, [userLat, userLng]);

  // Check backend health + load chat history
  useEffect(() => {
    async function init() {
      const online = await checkHealth();
      setBackendOnline(online);
      if (online) {
        try {
          const history = await getChatHistory();
          setChatMessages(history.messages);
        } catch {
          // ignore
        }
      }
    }
    init();
  }, []);

  function handleNewMessage(userMsg: ChatMessage, assistantMsg: ChatMessage) {
    setChatMessages((prev) => [...prev, userMsg, assistantMsg]);
  }

  return (
    <div className="min-h-screen bg-[#fafafa]">
      {/* Header */}
      <header className="bg-white border-b border-[#f0f0f0]">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 bg-[#18181b] rounded-lg flex items-center justify-center text-white text-sm font-semibold">
              N
            </div>
            <span className="text-base font-semibold text-[#18181b] tracking-tight">NutriCoach</span>
          </div>
          <div className="flex items-center gap-3">
            {locationStatus === 'denied' && (
              <span className="text-xs text-[#a1a1aa]">Using default location</span>
            )}
            <div className="flex items-center gap-1.5">
              <div className={`w-1.5 h-1.5 rounded-full ${backendOnline ? 'bg-green-500' : 'bg-[#d4d4d8]'}`} />
              <span className="text-xs text-[#a1a1aa]">{backendOnline ? 'Connected' : 'Backend offline'}</span>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-6xl mx-auto px-6 py-6">
        {/* Map */}
        <section className="mb-6">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-medium text-[#18181b]">Nearby Food Options</h2>
            <span className="text-xs text-[#a1a1aa]">{places.length} places found</span>
          </div>
          <FoodMap
            places={places}
            userLat={userLat}
            userLng={userLng}
          />
        </section>

        {/* Recommendations + Chat side by side */}
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
          {/* Recommendations */}
          <section className="lg:col-span-3">
            <h2 className="text-sm font-medium text-[#18181b] mb-3">Recommended for You</h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {recommendations.map((rec) => (
                <RecommendationCard key={rec.id} recommendation={rec} />
              ))}
            </div>
          </section>

          {/* Chat */}
          <section className="lg:col-span-2">
            <h2 className="text-sm font-medium text-[#18181b] mb-3">Ask the Coach</h2>
            <ChatPanel
              messages={chatMessages}
              onNewMessage={handleNewMessage}
              backendOnline={backendOnline}
            />
          </section>
        </div>
      </main>
    </div>
  );
}
