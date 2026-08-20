"use client";

import { AdviceCards } from "@/components/AdviceCards";
import { compareRegimes } from "@/lib/taxEngine";
import { useTaxProfile } from "@/lib/storage";
import type { TaxProfile } from "@/lib/types";

export default function ComparePage() {
  const [profile, saveProfile] = useTaxProfile();
  const advice = compareRegimes(profile);

  function updateSalary<K extends keyof TaxProfile["salary"]>(key: K, value: number) {
    const next = { ...profile, salary: { ...profile.salary, [key]: value } };
    saveProfile(next);
  }

  return (
    <div className="mx-auto max-w-6xl px-4 py-10">
      <h1 className="text-3xl font-semibold tracking-tight text-ink">Old vs new regime</h1>
      <p className="mt-2 max-w-2xl text-sm leading-6 text-muted">
        Edit the salary box if the parser missed a line. New regime is the legal default for Tax
        Year 2026-27.
      </p>
      <div className="mt-8 grid gap-8 lg:grid-cols-[0.8fr_1.2fr]">
        <div className="space-y-3 rounded-2xl border border-line bg-card p-4">
          <Field label="Basic" value={profile.salary.basic} onChange={(v) => updateSalary("basic", v)} />
          <Field label="HRA received" value={profile.salary.hraReceived} onChange={(v) => updateSalary("hraReceived", v)} />
          <Field label="Special allowance" value={profile.salary.specialAllowance} onChange={(v) => updateSalary("specialAllowance", v)} />
          <Field label="Bonus" value={profile.salary.bonus} onChange={(v) => updateSalary("bonus", v)} />
          <Field label="Employer NPS" value={profile.salary.employerNps} onChange={(v) => updateSalary("employerNps", v)} />
          <Field label="TDS" value={profile.salary.tds} onChange={(v) => updateSalary("tds", v)} />
          <Field
            label="Rent paid"
            value={profile.deductions.rentPaid}
            onChange={(v) => {
              const next = { ...profile, deductions: { ...profile.deductions, rentPaid: v } };
              saveProfile(next);
            }}
          />
        </div>
        <AdviceCards advice={advice} />
      </div>
    </div>
  );
}

function Field({
  label,
  value,
  onChange,
}: {
  label: string;
  value: number;
  onChange: (value: number) => void;
}) {
  return (
    <label className="block text-sm">
      <span className="text-muted">{label}</span>
      <input
        type="number"
        className="mt-1 w-full rounded-lg border border-line bg-background px-3 py-2"
        value={value}
        onChange={(e) => onChange(Number(e.target.value) || 0)}
      />
    </label>
  );
}
