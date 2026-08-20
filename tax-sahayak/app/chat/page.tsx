"use client";

import { useState } from "react";
import { loadProfile, useChatLog } from "@/lib/storage";
import type { ChatMessage } from "@/lib/types";

const prompts = [
  "Which regime should I choose?",
  "How can I save tax on this CTC?",
  "Explain my HRA exemption",
  "What is left in 80C?",
  "How do I file ITR-1?",
];

export default function ChatPage() {
  const [storedMessages, persistChat] = useChatLog();
  const [draft, setDraft] = useState<ChatMessage[] | null>(null);
  const messages = draft ?? storedMessages;
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);

  async function send(text: string) {
    const content = text.trim();
    if (!content || busy) return;
    const next = [...messages, { role: "user" as const, content }];
    setDraft(next);
    setInput("");
    setBusy(true);
    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: content, history: next, profile: loadProfile() }),
      });
      const data = await res.json();
      const withReply = [...next, { role: "assistant" as const, content: data.reply ?? data.error }];
      setDraft(withReply);
      persistChat(withReply);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto flex max-w-3xl flex-col px-4 py-8">
      <h1 className="text-3xl font-semibold tracking-tight text-ink">Tax savings chatbot</h1>
      <p className="mt-2 text-sm text-muted">
        Answers follow current India slabs and deduction limits. Not a substitute for a CA on
        litigation, NRI, or capital-gains facts.
      </p>
      <div className="mt-4 flex flex-wrap gap-2">
        {prompts.map((prompt) => (
          <button
            key={prompt}
            type="button"
            className="rounded-full border border-line bg-card px-3 py-1 text-xs hover:border-ink/30"
            onClick={() => send(prompt)}
          >
            {prompt}
          </button>
        ))}
      </div>
      <div className="mt-6 flex max-h-[520px] flex-col gap-3 overflow-y-auto rounded-2xl border border-line bg-card p-4">
        {messages.map((message, index) => (
          <article
            key={`${message.role}-${index}`}
            className={`max-w-[90%] whitespace-pre-wrap rounded-2xl px-4 py-3 text-sm leading-6 ${
              message.role === "user"
                ? "ml-auto bg-green text-white"
                : "bg-background text-ink"
            }`}
          >
            {message.content}
          </article>
        ))}
        {busy ? <p className="text-xs text-muted">Checking the tax engine…</p> : null}
      </div>
      <form
        className="mt-4 flex gap-2"
        onSubmit={(event) => {
          event.preventDefault();
          void send(input);
        }}
      >
        <input
          className="flex-1 rounded-full border border-line bg-card px-4 py-2.5 text-sm"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about 80C, HRA, NPS, or paste a salary line"
        />
        <button
          type="submit"
          disabled={busy}
          className="rounded-full bg-green px-5 py-2.5 text-sm font-medium text-white hover:bg-green-dark disabled:opacity-60"
        >
          Send
        </button>
      </form>
    </div>
  );
}
