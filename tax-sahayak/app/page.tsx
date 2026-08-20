import Link from "next/link";

const steps = [
  {
    n: "01",
    title: "Upload Form 16 or CTC",
    body: "PDF or text. We read basic, HRA, PF, TDS and offer-letter monthly lines.",
  },
  {
    n: "02",
    title: "Compare old vs new",
    body: "Default new regime slabs for Tax Year 2026-27, ₹75,000 standard deduction, ₹12 lakh rebate.",
  },
  {
    n: "03",
    title: "Ask the savings bot",
    body: "80C, HRA, NPS 80CCD(2), 80D and CTC restructuring — according to India law, not generic tips.",
  },
  {
    n: "04",
    title: "Prepare ITR-1",
    body: "Walk the salary, house, deductions and tax summary, then copy onto the government portal.",
  },
];

export default function Home() {
  return (
    <div>
      <section className="mx-auto grid max-w-6xl gap-10 px-4 py-14 lg:grid-cols-[1.2fr_0.8fr] lg:items-center">
        <div>
          <p className="text-sm font-medium text-saffron">Built for salaried India · Tax Year 2026-27</p>
          <h1 className="mt-2 max-w-xl text-4xl font-semibold tracking-tight text-ink sm:text-5xl">
            File your tax return. See where the law still lets you save.
          </h1>
          <p className="mt-4 max-w-xl text-base leading-7 text-muted">
            Sahayak Tax is a ClearTax-style workspace: ITR prep, old vs new regime, and a chatbot
            that reads your Form 16 or CTC offer letter. It does not replace the Income Tax portal
            — it gets the numbers honest before you go there.
          </p>
          <div className="mt-6 flex flex-wrap gap-3">
            <Link
              href="/upload"
              className="rounded-full bg-green px-5 py-2.5 text-sm font-medium text-white hover:bg-green-dark"
            >
              Upload Form 16
            </Link>
            <Link
              href="/chat"
              className="rounded-full border border-ink/15 bg-card px-5 py-2.5 text-sm font-medium text-ink hover:border-ink/30"
            >
              Open savings chatbot
            </Link>
          </div>
        </div>
        <div className="rounded-2xl border border-line bg-card p-5 shadow-sm">
          <p className="text-xs font-medium uppercase tracking-wide text-muted">New regime snapshot</p>
          <ul className="mt-3 space-y-2 text-sm text-ink">
            <li className="flex justify-between border-b border-line py-2"><span>Nil band</span><span>₹4 lakh</span></li>
            <li className="flex justify-between border-b border-line py-2"><span>Rebate (87A / successor)</span><span>tax-free till ₹12 lakh</span></li>
            <li className="flex justify-between border-b border-line py-2"><span>Standard deduction</span><span>₹75,000</span></li>
            <li className="flex justify-between py-2"><span>Top slab</span><span>30% above ₹24 lakh</span></li>
          </ul>
          <p className="mt-3 text-xs text-muted">Budget 2026 kept these Budget 2025 slabs. 4% cess extra.</p>
        </div>
      </section>
      <section className="border-t border-line bg-card/50">
        <div className="mx-auto grid max-w-6xl gap-6 px-4 py-12 sm:grid-cols-2 lg:grid-cols-4">
          {steps.map((step) => (
            <div key={step.n} className="rounded-xl border border-line bg-card p-4">
              <div className="text-xs font-semibold text-saffron">{step.n}</div>
              <h2 className="mt-1 text-base font-semibold text-ink">{step.title}</h2>
              <p className="mt-2 text-sm leading-6 text-muted">{step.body}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
