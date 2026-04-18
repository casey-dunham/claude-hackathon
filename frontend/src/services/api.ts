import type {
  ChatHistoryResponse,
  ChatResponse,
  CreateFoodEntryInput,
  DailySummary,
  FoodEntry,
  FoodLogResponse,
  HealthResponse,
  NearbyPlacesResponse,
  Profile,
} from "./types";

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/+$/, "");
const REQUEST_TIMEOUT_MS = 10000;

type QueryValue = string | number | undefined;

type ApiErrorResponse = {
  error?: {
    code?: string;
    message?: string;
  };
};

function buildUrl(path: string, query?: Record<string, QueryValue>): string {
  const params = new URLSearchParams();

  if (query) {
    for (const [key, value] of Object.entries(query)) {
      if (value !== undefined) {
        params.set(key, String(value));
      }
    }
  }

  const queryString = params.toString();
  const prefixedPath = path.startsWith("/") ? path : `/${path}`;
  const url = `${API_BASE_URL}${prefixedPath}`;
  return queryString ? `${url}?${queryString}` : url;
}

async function request<T>(
  path: string,
  options?: RequestInit,
  query?: Record<string, QueryValue>
): Promise<T> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  let response: Response;
  try {
    response = await fetch(buildUrl(path, query), {
      ...options,
      signal: controller.signal,
      headers: {
        Accept: "application/json",
        ...(options?.body ? { "Content-Type": "application/json" } : {}),
        ...options?.headers,
      },
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new Error("Request timed out. Confirm backend is running on 127.0.0.1:8000.");
    }
    throw error;
  } finally {
    clearTimeout(timeoutId);
  }

  if (!response.ok) {
    let message = `Request failed with status ${response.status}`;
    try {
      const payload = (await response.json()) as ApiErrorResponse;
      if (payload.error?.message) {
        message = payload.error.message;
      }
    } catch {
      // Keep fallback message when body is empty or invalid JSON.
    }
    throw new Error(message);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

export async function getHealth(): Promise<HealthResponse> {
  return request<HealthResponse>("/api/health");
}

export async function getNearbyPlaces(
  lat: number,
  lng: number,
  radiusM = 1200,
  limit = 12
): Promise<NearbyPlacesResponse> {
  return request<NearbyPlacesResponse>("/api/maps/nearby", undefined, {
    lat,
    lng,
    radius_m: radiusM,
    limit,
  });
}

export async function getTodaySummary(): Promise<DailySummary> {
  return request<DailySummary>("/api/dashboard/today");
}

export async function getDashboardHistory(days = 7): Promise<{ days: DailySummary[] }> {
  return request<{ days: DailySummary[] }>("/api/dashboard/history", undefined, { days });
}

export async function getLog(date?: string): Promise<FoodLogResponse> {
  return request<FoodLogResponse>("/api/log", undefined, { date });
}

export async function createLogEntry(payload: CreateFoodEntryInput): Promise<FoodEntry> {
  return request<FoodEntry>("/api/log", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function deleteLogEntry(entryId: string): Promise<void> {
  await request<void>(`/api/log/${entryId}`, { method: "DELETE" });
}

export async function getChatHistory(limit = 50): Promise<ChatHistoryResponse> {
  return request<ChatHistoryResponse>("/api/chat/history", undefined, { limit });
}

export async function postChat(message: string, lat?: number, lng?: number): Promise<ChatResponse> {
  return request<ChatResponse>("/api/chat", {
    method: "POST",
    body: JSON.stringify({ message, lat, lng }),
  });
}

export async function sendChatMessage(message: string, lat?: number, lng?: number): Promise<ChatResponse> {
  return postChat(message, lat, lng);
}

export async function getProfile(): Promise<Profile> {
  return request<Profile>("/api/profile");
}

export async function updateProfile(profile: Profile): Promise<Profile> {
  return request<Profile>("/api/profile", {
    method: "PUT",
    body: JSON.stringify(profile),
  });
}
