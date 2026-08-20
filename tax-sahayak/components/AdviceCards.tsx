import { inr } from "@/lib/money";
import type { AdvicePack, RegimeResult } from "@/lib/types";

export function AdviceCards({ advice }: { advice: AdvicePack }) {
  return (
    <div className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-2">
        <RegimeCard result={advice.new} winner={advice.recommended === "new"} />
        <RegimeCard result={advice.old} winner={advice.recommended === "old"} />
      </div>
      <p className="text-sm leading-6 text-ink">{advice.summary}</p>
      <ul className="space-y-3">
        {advice.tips.slice(0, 5).map((tip) => (
          <li key={tip.id} className="rounded-xl border border-line bg-card p-4">
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <h3 className="text-sm font-semibold text-ink">{tip.title}</h3>
              {tip.estimatedTaxSaved > 0 ? (
                <span className="text-sm font-medium text-green">saves {inr(tip.estimatedTaxSaved)}</span>
              ) : null}
            </div>
            <p className="mt-1 text-xs text-muted">
              {tip.section} · {tip.regime} regime
              {tip.extraInvestment > 0 ? ` · invest ${inr(tip.extraInvestment)}` : ""}
            </p>
            <p className="mt-2 text-sm leading-6 text-ink/90">{tip.detail}</p>
          </li>
        ))}
      </ul>
    </div>
  );
}

function RegimeCard({ result, winner }: { result: RegimeResult; winner: boolean }) {
  return (
    <div
      className={`rounded-xl border p-4 ${winner ? "border-green bg-green/5" : "border-line bg-card"}`}
    >
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold capitalize text-ink">{result.regime} regime</h3>
        {winner ? (
          <span className="rounded-full bg-green px-2 py-0.5 text-[11px] font-medium text-white">
            cheaper
          </span>
        ) : null}
      </div>
      <p className="money mt-2 text-2xl font-semibold text-ink">{inr(result.totalTax)}</p>
      <p className="text-xs text-muted">including 4% cess</p>
      <dl className="mt-3 space-y-1 text-xs text-muted">
        <div className="flex justify-between">
          <dt>Taxable income</dt>
          <dd className="money text-ink">{inr(result.taxableIncome)}</dd>
        </div>
        <div className="flex justify-between">
          <dt>Standard deduction</dt>
          <dd className="money text-ink">{inr(result.standardDeduction)}</dd>
        </div>
        <div className="flex justify-between">
          <dt>HRA exemption</dt>
          <dd className="money text-ink">{inr(result.hraExemption)}</dd>
        </div>
        <div className="flex justify-between">
          <dt>TDS</dt>
          <dd className="money text-ink">{inr(result.tds)}</dd>
        </div>
        <div className="flex justify-between">
          <dt>{result.payableOrRefund >= 0 ? "Likely refund" : "Tax still due"}</dt>
          <dd className="money text-ink">{inr(Math.abs(result.payableOrRefund))}</dd>
        </div>
      </dl>
    </div>
  );
}
