"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { AdviceCards } from "@/components/AdviceCards";
import { inr } from "@/lib/money";
import { useTaxProfile } from "@/lib/storage";
import { compareRegimes, TAX_YEAR } from "@/lib/taxEngine";
import type { AgeBand, CityType, Regime, TaxProfile } from "@/lib/types";

const steps = ["You", "Salary", "Deductions", "Review", "Acknowledgement"] as const;

export default function FilePage() {
  const [profile, saveProfile] = useTaxProfile();
  const [step, setStep] = useState(0);
  const [choice, setChoice] = useState<Regime>("new");
  const [ack, setAck] = useState("");
  const [picked, setPicked] = useState(false);

  const advice = useMemo(() => compareRegimes(profile), [profile]);
  const regime: Regime = picked ? choice : advice.recommended;

  function patch(next: TaxProfile) {
    saveProfile(next);
  }

  const result = regime === "new" ? advice.new : advice.old;

  return (
    <div className="mx-auto max-w-3xl px-4 py-10">
      <p className="text-xs font-medium uppercase tracking-wide text-saffron">
        ITR-1 (Sahaj) prep · Tax Year {TAX_YEAR}
      </p>
      <h1 className="mt-1 text-3xl font-semibold tracking-tight text-ink">File your return</h1>
      <ol className="mt-6 flex flex-wrap gap-2 text-xs">
        {steps.map((label, index) => (
          <li
            key={label}
            className={`rounded-full px-3 py-1 ${index === step ? "bg-green text-white" : "bg-card text-muted"}`}
          >
            {index + 1}. {label}
          </li>
        ))}
      </ol>

      <div className="mt-8 rounded-2xl border border-line bg-card p-6">
        {step === 0 ? (
          <div className="grid gap-4 sm:grid-cols-2">
            <TextField label="Full name" value={profile.name} onChange={(name) => patch({ ...profile, name })} />
            <TextField label="PAN" value={profile.pan} onChange={(pan) => patch({ ...profile, pan: pan.toUpperCase() })} />
            <TextField label="Employer" value={profile.employer} onChange={(employer) => patch({ ...profile, employer })} />
            <TextField label="TAN" value={profile.tan} onChange={(tan) => patch({ ...profile, tan: tan.toUpperCase() })} />
            <label className="text-sm">
              <span className="text-muted">Age band</span>
              <select
                className="mt-1 w-full rounded-lg border border-line bg-background px-3 py-2"
                value={profile.ageBand}
                onChange={(e) => patch({ ...profile, ageBand: e.target.value as AgeBand })}
              >
                <option value="below60">Below 60</option>
                <option value="senior">60–79 (senior)</option>
                <option value="superSenior">80+ (super senior)</option>
              </select>
            </label>
            <label className="text-sm">
              <span className="text-muted">HRA city</span>
              <select
                className="mt-1 w-full rounded-lg border border-line bg-background px-3 py-2"
                value={profile.city}
                onChange={(e) => patch({ ...profile, city: e.target.value as CityType })}
              >
                <option value="metro">Metro (Mumbai, Delhi, Kolkata, Chennai)</option>
                <option value="nonMetro">Non-metro</option>
              </select>
            </label>
          </div>
        ) : null}

        {step === 1 ? (
          <div className="grid gap-4 sm:grid-cols-2">
            <MoneyField label="Basic" value={profile.salary.basic} onChange={(basic) => patch({ ...profile, salary: { ...profile.salary, basic } })} />
            <MoneyField label="DA" value={profile.salary.da} onChange={(da) => patch({ ...profile, salary: { ...profile.salary, da } })} />
            <MoneyField label="HRA received" value={profile.salary.hraReceived} onChange={(hraReceived) => patch({ ...profile, salary: { ...profile.salary, hraReceived } })} />
            <MoneyField label="Special allowance" value={profile.salary.specialAllowance} onChange={(specialAllowance) => patch({ ...profile, salary: { ...profile.salary, specialAllowance } })} />
            <MoneyField label="Bonus / variable" value={profile.salary.bonus} onChange={(bonus) => patch({ ...profile, salary: { ...profile.salary, bonus } })} />
            <MoneyField label="LTA" value={profile.salary.lta} onChange={(lta) => patch({ ...profile, salary: { ...profile.salary, lta } })} />
            <MoneyField label="Employer PF" value={profile.salary.employerPf} onChange={(employerPf) => patch({ ...profile, salary: { ...profile.salary, employerPf } })} />
            <MoneyField label="Employer NPS" value={profile.salary.employerNps} onChange={(employerNps) => patch({ ...profile, salary: { ...profile.salary, employerNps } })} />
            <MoneyField label="Professional tax" value={profile.salary.professionalTax} onChange={(professionalTax) => patch({ ...profile, salary: { ...profile.salary, professionalTax } })} />
            <MoneyField label="TDS (Form 16)" value={profile.salary.tds} onChange={(tds) => patch({ ...profile, salary: { ...profile.salary, tds } })} />
            <MoneyField label="Other income (savings etc.)" value={profile.otherIncome} onChange={(otherIncome) => patch({ ...profile, otherIncome })} />
            <label className="flex items-center gap-2 text-sm sm:col-span-2">
              <input
                type="checkbox"
                checked={profile.livesInRentedHouse}
                onChange={(e) => patch({ ...profile, livesInRentedHouse: e.target.checked })}
              />
              I live in a rented house (needed for HRA)
            </label>
            <p className="sm:col-span-2 text-sm text-muted">
              Missing numbers? <Link className="text-green underline" href="/upload">Upload Form 16</Link>
            </p>
          </div>
        ) : null}

        {step === 2 ? (
          <div className="grid gap-4 sm:grid-cols-2">
            <MoneyField label="Employee PF (80C)" value={profile.deductions.employeePf} onChange={(employeePf) => patch({ ...profile, deductions: { ...profile.deductions, employeePf } })} />
            <MoneyField label="ELSS / PPF / LIC / other 80C" value={profile.deductions.elss + profile.deductions.ppf + profile.deductions.lifeInsurance + profile.deductions.other80C} onChange={(other80C) => patch({ ...profile, deductions: { ...profile.deductions, elss: 0, ppf: 0, lifeInsurance: 0, other80C } })} />
            <MoneyField label="NPS extra 80CCD(1B)" value={profile.deductions.npsAdditional80CCD1B} onChange={(npsAdditional80CCD1B) => patch({ ...profile, deductions: { ...profile.deductions, npsAdditional80CCD1B } })} />
            <MoneyField label="Health insurance 80D (self)" value={profile.deductions.healthInsuranceSelf} onChange={(healthInsuranceSelf) => patch({ ...profile, deductions: { ...profile.deductions, healthInsuranceSelf } })} />
            <MoneyField label="Health insurance 80D (parents)" value={profile.deductions.healthInsuranceParents} onChange={(healthInsuranceParents) => patch({ ...profile, deductions: { ...profile.deductions, healthInsuranceParents } })} />
            <MoneyField label="Home loan interest 24(b)" value={profile.deductions.homeLoanInterest} onChange={(homeLoanInterest) => patch({ ...profile, deductions: { ...profile.deductions, homeLoanInterest } })} />
            <MoneyField label="Home loan principal (80C)" value={profile.deductions.homeLoanPrincipal} onChange={(homeLoanPrincipal) => patch({ ...profile, deductions: { ...profile.deductions, homeLoanPrincipal } })} />
            <MoneyField label="Rent paid" value={profile.deductions.rentPaid} onChange={(rentPaid) => patch({ ...profile, deductions: { ...profile.deductions, rentPaid } })} />
            <MoneyField label="Education loan interest 80E" value={profile.deductions.educationLoanInterest} onChange={(educationLoanInterest) => patch({ ...profile, deductions: { ...profile.deductions, educationLoanInterest } })} />
            <label className="flex items-center gap-2 text-sm sm:col-span-2">
              <input
                type="checkbox"
                checked={profile.deductions.parentsAreSenior}
                onChange={(e) =>
                  patch({
                    ...profile,
                    deductions: { ...profile.deductions, parentsAreSenior: e.target.checked },
                  })
                }
              />
              Parents are senior citizens (80D limit ₹50,000)
            </label>
          </div>
        ) : null}

        {step === 3 ? (
          <div className="space-y-6">
            <div>
              <p className="text-sm font-medium text-ink">Choose regime for this return</p>
              <div className="mt-2 flex gap-2">
                <button
                  type="button"
                  className={`rounded-full px-4 py-2 text-sm ${regime === "new" ? "bg-green text-white" : "border border-line"}`}
                  onClick={() => {
                    setPicked(true);
                    setChoice("new");
                  }}
                >
                  New (default)
                </button>
                <button
                  type="button"
                  className={`rounded-full px-4 py-2 text-sm ${regime === "old" ? "bg-green text-white" : "border border-line"}`}
                  onClick={() => {
                    setPicked(true);
                    setChoice("old");
                  }}
                >
                  Old (opt-in)
                </button>
              </div>
            </div>
            <AdviceCards advice={advice} />
            <div className="rounded-xl bg-background p-4 text-sm">
              <div className="flex justify-between py-1">
                <span>Tax on chosen regime</span>
                <span className="money font-semibold">{inr(result.totalTax)}</span>
              </div>
              <div className="flex justify-between py-1">
                <span>TDS</span>
                <span className="money">{inr(result.tds)}</span>
              </div>
              <div className="flex justify-between py-1">
                <span>{result.payableOrRefund >= 0 ? "Refund" : "Balance tax"}</span>
                <span className="money font-semibold">{inr(Math.abs(result.payableOrRefund))}</span>
              </div>
            </div>
          </div>
        ) : null}

        {step === 4 ? (
          <div className="space-y-3 text-sm leading-6">
            <p className="text-lg font-semibold text-ink">
              {ack || "Preview ready — this app does not upload to the Income Tax Department."}
            </p>
            <p>
              Assessee: <strong>{profile.name || "Not filled"}</strong> · PAN{" "}
              <strong>{profile.pan || "—"}</strong>
            </p>
            <p>
              Regime: <strong>{regime}</strong> · Tax {inr(result.totalTax)} · TDS {inr(result.tds)}
            </p>
            <p className="text-muted">
              Copy these figures into ITR-1 on{" "}
              <a className="text-green underline" href="https://eportal.incometax.gov.in" target="_blank" rel="noreferrer">
                eportal.incometax.gov.in
              </a>
              . Keep Form 16, rent receipts and 80C proofs.
            </p>
          </div>
        ) : null}
      </div>

      <div className="mt-6 flex justify-between">
        <button
          type="button"
          className="rounded-full border border-line px-4 py-2 text-sm disabled:opacity-40"
          disabled={step === 0}
          onClick={() => setStep((s) => s - 1)}
        >
          Back
        </button>
        {step < 4 ? (
          <button
            type="button"
            className="rounded-full bg-green px-5 py-2 text-sm font-medium text-white hover:bg-green-dark"
            onClick={() => {
              if (step === 3) {
                const id = `SAHAYAK-${TAX_YEAR}-${Math.random().toString(36).slice(2, 8).toUpperCase()}`;
                setAck(`Demo acknowledgement ${id} generated ${new Date().toLocaleString("en-IN")}.`);
              }
              setStep((s) => s + 1);
            }}
          >
            {step === 3 ? "Generate demo acknowledgement" : "Continue"}
          </button>
        ) : (
          <Link href="/chat" className="rounded-full bg-green px-5 py-2 text-sm font-medium text-white">
            Ask savings bot
          </Link>
        )}
      </div>
    </div>
  );
}

function TextField({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <label className="text-sm">
      <span className="text-muted">{label}</span>
      <input
        className="mt-1 w-full rounded-lg border border-line bg-background px-3 py-2"
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
    </label>
  );
}

function MoneyField({
  label,
  value,
  onChange,
}: {
  label: string;
  value: number;
  onChange: (value: number) => void;
}) {
  return (
    <label className="text-sm">
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
