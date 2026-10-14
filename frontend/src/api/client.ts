import { createSseParser } from "./stream";
import type { EvalResults, OrderBlock, StreamEvent } from "./types";

export const API_URL = (import.meta.env.VITE_API_URL ?? "http://localhost:8000").replace(/\/$/, "");
const SESSION_HEADER = "X-Session-Id";

export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message);
  }
}

async function errorFrom(response: Response): Promise<ApiError> {
  const body = await response.json().catch(() => null);
  const detail = typeof body?.detail === "string" ? body.detail : `Request failed (${response.status})`;
  return new ApiError(response.status, detail);
}

export async function streamChat(
  message: string,
  sessionId: string | null,
  confirmToken: string | null,
  onEvent: (event: StreamEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const response = await fetch(`${API_URL}/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...(sessionId ? { [SESSION_HEADER]: sessionId } : {}) },
    body: JSON.stringify({ message, confirm_token: confirmToken }),
    signal,
  });
  if (!response.ok || !response.body) throw await errorFrom(response);

  const parse = createSseParser(onEvent);
  const reader = response.body.pipeThrough(new TextDecoderStream()).getReader();
  for (;;) {
    const { value, done } = await reader.read();
    if (done) return;
    parse(value);
  }
}

export async function fetchOrders(sessionId: string): Promise<OrderBlock[]> {
  const response = await fetch(`${API_URL}/orders`, { headers: { [SESSION_HEADER]: sessionId } });
  if (!response.ok) throw await errorFrom(response);
  return response.json();
}

export async function fetchHealth(signal?: AbortSignal): Promise<boolean> {
  const response = await fetch(`${API_URL}/health`, { signal });
  return response.ok;
}

export async function fetchEvals(): Promise<EvalResults | null> {
  const response = await fetch(`${API_URL}/evals`);
  if (response.status === 404) return null;
  if (!response.ok) throw await errorFrom(response);
  return response.json();
}
