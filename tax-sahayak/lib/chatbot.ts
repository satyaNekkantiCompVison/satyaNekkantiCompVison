import { compareRegimes, SECTION_80C_LIMIT, TAX_YEAR } from "./taxEngine";
import type { ChatMessage, TaxProfile } from "./types";
import { inr } from "./money";

function hasIncome(profile: TaxProfile): boolean {
  return (
    profile.salary.basic +
      profile.salary.specialAllowance +
      profile.salary.hraReceived +
      profile.salary.bonus >
    0
  );
}

function regimeAnswer(profile: TaxProfile): string {
  const pack = compareRegimes(profile);
  return [
    `For Tax Year ${TAX_YEAR} I compared both regimes on the numbers in your profile.`,
    ``,
    `• New regime tax: **${inr(pack.new.totalTax)}** (taxable ${inr(pack.new.taxableIncome)})`,
    `• Old regime tax: **${inr(pack.old.totalTax)}** (taxable ${inr(pack.old.taxableIncome)})`,
    `• HRA exemption (old only): ${inr(pack.old.hraExemption)}`,
    `• Standard deduction: new ${inr(pack.new.standardDeduction)} vs old ${inr(pack.old.standardDeduction)}`,
    ``,
    `**Recommendation: ${pack.recommended === "new" ? "new regime (default)" : "opt for old regime"}.** ${pack.summary}`,
    ``,
    `TDS already deducted: ${inr(profile.salary.tds)}. ${
      pack[pack.recommended].payableOrRefund >= 0
        ? `Likely refund about ${inr(pack[pack.recommended].payableOrRefund)} if this TDS is correct.`
        : `Likely extra tax of ${inr(-pack[pack.recommended].payableOrRefund)} at filing.`
    }`,
  ].join("\n");
}

function savingsAnswer(profile: TaxProfile): string {
  const pack = compareRegimes(profile);
  const lines = [
    `Here are India-law savings ideas ranked for your Form 16 / CTC. This is guidance, not a CA opinion.`,
    ``,
  ];
  for (const tip of pack.tips.slice(0, 6)) {
    lines.push(`**${tip.title}** (${tip.section}, ${tip.regime} regime)`);
    lines.push(tip.detail);
    if (tip.extraInvestment > 0) {
      lines.push(`Invest / claim up to ${inr(tip.extraInvestment)}.`);
    }
    if (tip.estimatedTaxSaved > 0) {
      lines.push(`Estimated tax saved: **${inr(tip.estimatedTaxSaved)}**.`);
    }
    lines.push("");
  }
  lines.push(
    "New-regime reminder: 80C, 80D and HRA do not reduce tax there. Employer NPS under 80CCD(2) still does.",
  );
  return lines.join("\n");
}

function slabsAnswer(): string {
  return [
    `**New regime slabs (Tax Year ${TAX_YEAR}, default)**`,
    `0–4L nil · 4–8L 5% · 8–12L 10% · 12–16L 15% · 16–20L 20% · 20–24L 25% · above 24L 30%.`,
    `Rebate makes tax nil if taxable income is up to ₹12 lakh (max rebate ₹60,000). Salaried standard deduction is ₹75,000, so many people pay nil tax up to ₹12.75 lakh gross.`,
    ``,
    `**Old regime (opt-in)**`,
    `Below 60: 0–2.5L nil · 2.5–5L 5% · 5–10L 20% · above 10L 30%. Standard deduction ₹50,000. 87A rebate only if taxable income ≤ ₹5 lakh.`,
    `4% health and education cess applies on tax + surcharge in both regimes.`,
    ``,
    `Budget 2026 did not change these slabs. Income-tax Act, 2025 applies from 1 Apr 2026 (Tax Year instead of AY/PY).`,
  ].join("\n");
}

function fileAnswer(): string {
  return [
    `You can prepare an ITR-1 (Sahaj) style return in this app, then copy the figures onto the Income Tax Department portal.`,
    ``,
    `Typical salaried path for Tax Year ${TAX_YEAR}:`,
    `1. Upload Form 16 (and AIS/TIS later if you have it).`,
    `2. Confirm HRA rent, 80C, 80D, housing loan.`,
    `3. Compare old vs new — new is default.`,
    `4. Review tax vs TDS.`,
    `5. File on https://eportal.incometax.gov.in — this demo does not submit to the department.`,
    ``,
    `ITR-1 is for residents with salary, one house, and other income up to ₹50 lakh without business income. Capital gains or more than one house usually means ITR-2.`,
  ].join("\n");
}

function ctcAnswer(profile: TaxProfile): string {
  const pack = compareRegimes(profile);
  return [
    `I read this as a CTC / offer letter. CTC is not the same as taxable salary: employer PF, gratuity and NPS sit in CTC but are not fully taxed as salary.`,
    ``,
    `Parsed CTC about **${inr(pack.new.ctc)}**, gross salary **${inr(pack.new.grossSalary)}**.`,
    ``,
    `Tax-efficient structure under India law:`,
    `• Basic around 40% of CTC (EPF is 12% of basic).`,
    `• HRA 40–50% of basic if you will pay rent.`,
    `• Employer NPS 10% of basic+DA — deductible even in the new regime (80CCD(2)).`,
    `• Food voucher / gadget / LTA as per company policy.`,
    `• Avoid stuffing everything into special allowance.`,
    ``,
    savingsAnswer(profile),
  ].join("\n");
}

export function answerChat(
  question: string,
  history: ChatMessage[],
  profile: TaxProfile,
): string {
  const q = question.toLowerCase();
  const incomeReady = hasIncome(profile);

  if (/slab|rate|budget 2026|new regime slab|old regime slab/.test(q)) {
    return slabsAnswer();
  }
  if (/how to file|itr-?1|e-?file|due date|portal/.test(q)) {
    return fileAnswer();
  }
  if (!incomeReady) {
    return [
      `I can do this properly once I have salary numbers. Upload Form 16 or a CTC offer letter, or type figures like:`,
      `\`Basic 800000, HRA 400000, special 500000, PF 96000, rent 360000\``,
      ``,
      slabsAnswer(),
    ].join("\n");
  }
  if (/compare|which regime|old vs new|new vs old|should i opt/.test(q)) {
    return regimeAnswer(profile);
  }
  if (/ctc|offer letter|restructur|salary structure/.test(q)) {
    return ctcAnswer(profile);
  }
  if (/80c|elss|ppf|epf|provident/.test(q)) {
    const used =
      profile.deductions.employeePf +
      profile.deductions.elss +
      profile.deductions.lifeInsurance +
      profile.deductions.ppf +
      profile.deductions.homeLoanPrincipal +
      profile.deductions.tuitionFees +
      profile.deductions.other80C +
      profile.deductions.npsEmployee;
    return [
      `Section 80C cap is ${inr(SECTION_80C_LIMIT)} and it only reduces tax in the **old** regime.`,
      `You currently have about **${inr(used)}** counting towards 80C (employee PF is included).`,
      leftoverLine(used),
      ``,
      regimeAnswer(profile),
    ].join("\n");
  }
  if (/hra|rent/.test(q)) {
    const pack = compareRegimes(profile);
    return [
      `HRA exemption is available only in the old regime under section 10(13A).`,
      `It is the least of: actual HRA (${inr(profile.salary.hraReceived)}), rent paid minus 10% of basic+DA, and 50% of basic+DA in metros (40% otherwise).`,
      `Computed exemption with your rent of ${inr(profile.deductions.rentPaid)}: **${inr(pack.old.hraExemption)}**.`,
      `If annual rent to one landlord is over ₹1 lakh, quote their PAN.`,
    ].join("\n");
  }
  if (/nps|80ccd/.test(q)) {
    return savingsAnswer(profile);
  }
  if (/80d|health|insurance/.test(q)) {
    return [
      `Section 80D (old regime): ₹25,000 for self/family, ₹50,000 if you are a senior citizen. Parents have a separate ₹25,000 / ₹50,000 limit.`,
      `Preventive health check-up of up to ₹5,000 sits inside that limit.`,
      `This deduction is not available in the new regime.`,
    ].join("\n");
  }
  if (/home loan|24b|housing|section 24/.test(q)) {
    return [
      `Self-occupied house: interest deduction up to ₹2 lakh under section 24(b) — old regime.`,
      `Principal repaid can go into 80C (shared with EPF/ELSS).`,
      `Let-out property: interest is deductible with set-off rules; loss from house property set-off is capped at ₹2 lakh against other heads.`,
      `New regime does not give the self-occupied 24(b) benefit.`,
    ].join("\n");
  }

  const lastUser = history.filter((m) => m.role === "user").at(-1)?.content ?? "";
  if (lastUser && lastUser === question) {
    // fall through
  }
  return [regimeAnswer(profile), "", savingsAnswer(profile)].join("\n");
}

function leftoverLine(used: number): string {
  const left = Math.max(0, SECTION_80C_LIMIT - used);
  if (left <= 0) return "Your 80C basket looks full.";
  return `Room left: **${inr(left)}**. ELSS, PPF, term insurance, Sukanya or home-loan principal can fill it.`;
}
