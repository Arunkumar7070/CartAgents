import { useCallback, useReducer, useRef } from "react";
import { ApiError, streamChat } from "../api/client";
import type { Block, ChatResponse, ConfirmationBlock, StreamEvent } from "../api/types";

export type Entry =
  | { id: number; role: "user"; text: string }
  | { id: number; role: "agent"; blocks: Block[] }
  | { id: number; role: "error"; message: string };

export type Pending = { token: string; action: ConfirmationBlock["action"] };

type Streaming = { node: string | null; draft: string };

export type ChatState = {
  entries: Entry[];
  sessionId: string | null;
  pending: Pending | null;
  streaming: Streaming | null;
  turn: number;
};

type Action =
  | { type: "sent"; text: string }
  | { type: "session"; sessionId: string | null }
  | { type: "step"; node: string }
  | { type: "delta"; text: string }
  | { type: "done"; response: ChatResponse }
  | { type: "failed"; message: string }
  | { type: "reset" };

const SESSION_KEY = "cartagent.session";

function readStoredSession(): string | null {
  try {
    return localStorage.getItem(SESSION_KEY);
  } catch {
    return null;
  }
}

function storeSession(sessionId: string | null) {
  try {
    if (sessionId) localStorage.setItem(SESSION_KEY, sessionId);
    else localStorage.removeItem(SESSION_KEY);
  } catch {
    return;
  }
}

function pendingFrom(response: ChatResponse): Pending | null {
  if (!response.pending_confirmation || !response.confirm_token) return null;
  const confirmation = response.blocks.find((b): b is ConfirmationBlock => b.type === "confirmation");
  return confirmation ? { token: response.confirm_token, action: confirmation.action } : null;
}

let nextId = 1;

export function chatReducer(state: ChatState, action: Action): ChatState {
  switch (action.type) {
    case "sent":
      return {
        ...state,
        entries: [...state.entries, { id: nextId++, role: "user", text: action.text }],
        streaming: { node: null, draft: "" },
      };
    case "session":
      return { ...state, sessionId: action.sessionId };
    case "step":
      return state.streaming ? { ...state, streaming: { ...state.streaming, node: action.node } } : state;
    case "delta":
      return state.streaming
        ? { ...state, streaming: { ...state.streaming, draft: state.streaming.draft + action.text } }
        : state;
    case "done":
      return {
        ...state,
        sessionId: action.response.session_id,
        entries: [...state.entries, { id: nextId++, role: "agent", blocks: action.response.blocks }],
        pending: pendingFrom(action.response),
        streaming: null,
        turn: state.turn + 1,
      };
    case "failed":
      return {
        ...state,
        entries: [...state.entries, { id: nextId++, role: "error", message: action.message }],
        streaming: null,
      };
    case "reset":
      return { entries: [], sessionId: null, pending: null, streaming: null, turn: state.turn + 1 };
  }
}

export function useChat() {
  const [state, dispatch] = useReducer(chatReducer, undefined, () => ({
    entries: [],
    sessionId: readStoredSession(),
    pending: null,
    streaming: null,
    turn: 0,
  }));
  const stateRef = useRef(state);
  stateRef.current = state;

  const send = useCallback(async (text: string) => {
    const message = text.trim();
    if (!message || stateRef.current.streaming) return;
    dispatch({ type: "sent", text: message });

    const handle = (event: StreamEvent) => {
      if (event.event === "session") {
        storeSession(event.data.session_id);
        dispatch({ type: "session", sessionId: event.data.session_id });
      } else if (event.event === "step" && event.data.status === "start") {
        dispatch({ type: "step", node: event.data.node });
      } else if (event.event === "delta") {
        dispatch({ type: "delta", text: event.data.text });
      } else if (event.event === "done") {
        dispatch({ type: "done", response: event.data });
      } else if (event.event === "error") {
        dispatch({ type: "failed", message: event.data.message });
      }
    };

    const attempt = (sessionId: string | null) =>
      streamChat(message, sessionId, stateRef.current.pending?.token ?? null, handle);

    try {
      await attempt(stateRef.current.sessionId);
    } catch (error) {
      if (error instanceof ApiError && error.status === 404) {
        storeSession(null);
        dispatch({ type: "session", sessionId: null });
        try {
          await attempt(null);
          return;
        } catch (retryError) {
          dispatch({ type: "failed", message: describe(retryError) });
          return;
        }
      }
      dispatch({ type: "failed", message: describe(error) });
    }
  }, []);

  const reset = useCallback(() => {
    storeSession(null);
    dispatch({ type: "reset" });
  }, []);

  return { state, send, reset };
}

function describe(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  return "The counter is unreachable right now. Check your connection and try again.";
}
