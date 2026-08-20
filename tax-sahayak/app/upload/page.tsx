"use client";

import { useMemo, useState } from "react";
import { AdviceCards } from "@/components/AdviceCards";
import { loadProfile, saveProfile } from "@/lib/storage";
import { compareRegimes, mergeProfile } from "@/lib/taxEngine";
import type { AdvicePack, TaxProfile } from "@/lib/types";

export default function UploadPage() {
  const [status, setStatus] = useState<string>("");
  const [advice, setAdvice] = useState<AdvicePack | null>(null);
  const [profile, setProfile] = useState<TaxProfile | null>(null);
  const [text, setText] = useState("");

  async function parse(form: FormData) {
    setStatus("Reading document…");
    const res = await fetch("/api/parse", { method: "POST", body: form });
    const data = await res.json();
    if (!res.ok) {
      setStatus(data.error ?? "Could not parse that file.");
      return;
    }
    const next = mergeProfile(loadProfile(), data.profile);
    saveProfile(next);
    setProfile(next);
    setAdvice(data.advice as AdvicePack);
    setStatus(
      `Parsed ${data.profile.documentKind === "ctc" ? "CTC / offer letter" : data.profile.documentKind === "form16" ? "Form 16" : "document"}. Review the figures, then open the chatbot.`,
    );
  }

  return (
    <div className="mx-auto max-w-6xl px-4 py-10">
      <h1 className="text-3xl font-semibold tracking-tight text-ink">Upload Form 16 or CTC</h1>
      <p className="mt-2 max-w-2xl text-sm leading-6 text-muted">
        Drop a PDF, a .txt export, or paste the salary table from your offer letter. Numbers stay
        in this browser. Use the samples if you want to try the flow first.
      </p>
      <div className="mt-6 grid gap-8 lg:grid-cols-[0.95fr_1.05fr]">
        <form
          className="space-y-4"
          onSubmit={async (event) => {
            event.preventDefault();
            const form = new FormData(event.currentTarget);
            if (text.trim()) form.set("text", text);
            await parse(form);
          }}
        >
          <label className="block rounded-2xl border border-dashed border-green/40 bg-card p-6 text-sm">
            <span className="font-medium text-ink">PDF or text file</span>
            <input
              className="mt-3 block w-full text-sm"
              type="file"
              name="file"
              accept=".pdf,.txt,.text,application/pdf,text/plain"
            />
          </label>
          <label className="block text-sm">
            <span className="font-medium text-ink">Or paste the document</span>
            <textarea
              className="mt-2 h-40 w-full rounded-xl border border-line bg-card p-3 font-mono text-xs"
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="Basic per month: 80000&#10;HRA per month: 40000"
            />
          </label>
          <div className="flex flex-wrap gap-2">
            <button
              type="submit"
              className="rounded-full bg-green px-5 py-2 text-sm font-medium text-white hover:bg-green-dark"
            >
              Extract and advise
            </button>
            <SampleButton label="Load sample Form 16" href="/samples/form16-sample.txt" onText={setText} />
            <SampleButton label="Load sample CTC" href="/samples/ctc-sample.txt" onText={setText} />
          </div>
          {status ? <p className="text-sm text-muted">{status}</p> : null}
        </form>
        <div>
          {advice && profile ? (
            <AdviceCards advice={advice} />
          ) : (
            <EmptyHint />
          )}
        </div>
      </div>
    </div>
  );
}

function SampleButton({
  label,
  href,
  onText,
}: {
  label: string;
  href: string;
  onText: (value: string) => void;
}) {
  return (
    <button
      type="button"
      className="rounded-full border border-line bg-card px-4 py-2 text-sm hover:border-ink/30"
      onClick={async () => {
        const res = await fetch(href);
        onText(await res.text());
      }}
    >
      {label}
    </button>
  );
}

function EmptyHint() {
  const demo = useMemo(() => compareRegimes(loadProfile()), []);
  if (demo.new.grossSalary === 0) {
    return (
      <div className="rounded-2xl border border-line bg-card p-6 text-sm leading-6 text-muted">
        After we read the document you will see old vs new tax, HRA, and a ranked savings list
        (80C leftover, NPS, employer NPS, health cover, CTC split).
      </div>
    );
  }
  return <AdviceCards advice={demo} />;
}
