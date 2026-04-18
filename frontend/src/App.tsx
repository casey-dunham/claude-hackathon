import { useEffect, useState } from 'react';
import ChatPanel from './components/ChatPanel';
import { getChatHistory, getHealth, getLog } from './services/api';
import { ChatMessage, FoodEntry } from './services/types';

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
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [entries, setEntries] = useState<FoodEntry[]>([]);
  const [backendOnline, setBackendOnline] = useState(false);
  const [isLogLoading, setIsLogLoading] = useState(true);
  const [logError, setLogError] = useState<string | null>(null);

  async function refreshLog() {
    const response = await getLog();
    setEntries(sortEntries(response.entries));
  }

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
        <section className="lg:col-span-2">
          <h2 className="mb-3 text-sm font-medium text-[#18181b]">Ask the Coach</h2>
          <ChatPanel
            messages={chatMessages}
            onNewMessage={handleNewMessage}
            backendOnline={backendOnline}
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
            <div className="space-y-2">
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
      </main>
    </div>
  );
}
