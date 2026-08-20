"use client";

import { useCallback, useSyncExternalStore } from "react";
import { defaultProfile, mergeProfile } from "./taxEngine";
import type { ChatMessage, TaxProfile } from "./types";

const PROFILE_KEY = "sahayak-tax-profile";
const CHAT_KEY = "sahayak-tax-chat";
const listeners = new Set<() => void>();

function emit() {
  listeners.forEach((listener) => listener());
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function loadProfile(): TaxProfile {
  if (typeof window === "undefined") return defaultProfile();
  try {
    const raw = localStorage.getItem(PROFILE_KEY);
    if (!raw) return defaultProfile();
    return mergeProfile(defaultProfile(), JSON.parse(raw) as Partial<TaxProfile>);
  } catch {
    return defaultProfile();
  }
}

export function saveProfile(profile: TaxProfile): void {
  localStorage.setItem(PROFILE_KEY, JSON.stringify(profile));
  emit();
}

export function loadChat(): ChatMessage[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(CHAT_KEY);
    return raw ? (JSON.parse(raw) as ChatMessage[]) : [];
  } catch {
    return [];
  }
}

export function saveChat(messages: ChatMessage[]): void {
  localStorage.setItem(CHAT_KEY, JSON.stringify(messages.slice(-40)));
  emit();
}

export function useTaxProfile(): [TaxProfile, (profile: TaxProfile) => void] {
  const json = useSyncExternalStore(
    subscribe,
    () => localStorage.getItem(PROFILE_KEY),
    () => null,
  );
  let profile = defaultProfile();
  if (json) {
    try {
      profile = mergeProfile(defaultProfile(), JSON.parse(json) as Partial<TaxProfile>);
    } catch {
      profile = defaultProfile();
    }
  }
  return [profile, saveProfile];
}

export function useChatLog(): [ChatMessage[], (messages: ChatMessage[]) => void] {
  const json = useSyncExternalStore(
    subscribe,
    () => localStorage.getItem(CHAT_KEY),
    () => null,
  );
  const welcome: ChatMessage[] = [
    {
      role: "assistant",
      content:
        "Namaste. I am the Sahayak savings bot for Indian income tax (Tax Year 2026-27). Upload Form 16 or a CTC letter first if you can — then ask about old vs new regime, 80C, HRA, NPS or filing.",
    },
  ];
  let messages = welcome;
  if (json) {
    try {
      messages = JSON.parse(json) as ChatMessage[];
    } catch {
      messages = welcome;
    }
  }
  const setMessages = useCallback((next: ChatMessage[]) => saveChat(next), []);
  return [messages, setMessages];
}
