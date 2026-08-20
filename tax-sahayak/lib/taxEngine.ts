import type {
  AdvicePack,
  AgeBand,
  DeductionInputs,
  Regime,
  RegimeResult,
  SalaryBreakdown,
  SavingTip,
  SlabLine,
  TaxProfile,
} from "./types";
import { clamp } from "./money";

/** Tax Year 2026-27 (Income-tax Act, 2025). Slabs unchanged from Budget 2025. */
export const TAX_YEAR = "2026-27";
export const CESS_RATE = 0.04;
export const STANDARD_DEDUCTION_NEW = 75_000;
export const STANDARD_DEDUCTION_OLD = 50_000;
export const REBATE_NEW_LIMIT = 1_200_000;
export const REBATE_NEW_MAX = 60_000;
export const REBATE_OLD_LIMIT = 500_000;
export const REBATE_OLD_MAX = 12_500;
export const SECTION_80C_LIMIT = 150_000;
export const SECTION_80CCD1B_LIMIT = 50_000;
export const SECTION_80D_SELF_LIMIT = 25_000;
export const SECTION_80D_SELF_SENIOR_LIMIT = 50_000;
export const SECTION_80D_PARENTS_LIMIT = 25_000;
export const SECTION_80D_PARENTS_SENIOR_LIMIT = 50_000;
export const SECTION_24B_LIMIT = 200_000;
export const SECTION_80TTA_LIMIT = 10_000;

export const NEW_SLABS: { to: number | null; rate: number }[] = [
  { to: 400_000, rate: 0 },
  { to: 800_000, rate: 0.05 },
  { to: 1_200_000, rate: 0.1 },
  { to: 1_600_000, rate: 0.15 },
  { to: 2_000_000, rate: 0.2 },
  { to: 2_400_000, rate: 0.25 },
  { to: null, rate: 0.3 },
];

const OLD_SLABS: Record<AgeBand, { to: number | null; rate: number }[]> = {
  below60: [
    { to: 250_000, rate: 0 },
    { to: 500_000, rate: 0.05 },
    { to: 1_000_000, rate: 0.2 },
    { to: null, rate: 0.3 },
  ],
  senior: [
    { to: 300_000, rate: 0 },
    { to: 500_000, rate: 0.05 },
    { to: 1_000_000, rate: 0.2 },
    { to: null, rate: 0.3 },
  ],
  superSenior: [
    { to: 500_000, rate: 0 },
    { to: 1_000_000, rate: 0.2 },
    { to: null, rate: 0.3 },
  ],
};

export function emptySalary(): SalaryBreakdown {
  return {
    basic: 0,
    da: 0,
    hraReceived: 0,
    lta: 0,
    specialAllowance: 0,
    otherAllowances: 0,
    bonus: 0,
    employerPf: 0,
    employerNps: 0,
    gratuity: 0,
    professionalTax: 0,
    tds: 0,
  };
}

export function emptyDeductions(): DeductionInputs {
  return {
    employeePf: 0,
    elss: 0,
    lifeInsurance: 0,
    ppf: 0,
    homeLoanPrincipal: 0,
    tuitionFees: 0,
    other80C: 0,
    npsEmployee: 0,
    npsAdditional80CCD1B: 0,
    healthInsuranceSelf: 0,
    healthInsuranceParents: 0,
    parentsAreSenior: false,
    homeLoanInterest: 0,
    rentPaid: 0,
    educationLoanInterest: 0,
    savingsInterest: 0,
    donations80G: 0,
  };
}

export function defaultProfile(): TaxProfile {
  return {
    name: "",
    pan: "",
    employer: "",
    tan: "",
    ageBand: "below60",
    city: "metro",
    livesInRentedHouse: true,
    fy: TAX_YEAR,
    salary: emptySalary(),
    otherIncome: 0,
    housePropertyLetOut: 0,
    deductions: emptyDeductions(),
  };
}

export function grossSalary(salary: SalaryBreakdown): number {
  return (
    salary.basic +
    salary.da +
    salary.hraReceived +
    salary.lta +
    salary.specialAllowance +
    salary.otherAllowances +
    salary.bonus
  );
}

export function ctcOf(salary: SalaryBreakdown): number {
  return (
    grossSalary(salary) +
    salary.employerPf +
    salary.employerNps +
    salary.gratuity
  );
}

export function hraExemption(profile: TaxProfile): number {
  const { salary, deductions, city, livesInRentedHouse } = profile;
  if (!livesInRentedHouse || salary.hraReceived <= 0 || deductions.rentPaid <= 0) {
    return 0;
  }
  const salaryForHra = salary.basic + salary.da;
  const excessRent = Math.max(0, deductions.rentPaid - 0.1 * salaryForHra);
  const metroShare = (city === "metro" ? 0.5 : 0.4) * salaryForHra;
  return Math.max(0, Math.min(salary.hraReceived, excessRent, metroShare));
}

function section80C(d: DeductionInputs): number {
  const used =
    d.employeePf +
    d.elss +
    d.lifeInsurance +
    d.ppf +
    d.homeLoanPrincipal +
    d.tuitionFees +
    d.other80C +
    d.npsEmployee;
  return clamp(used, 0, SECTION_80C_LIMIT);
}

function section80D(profile: TaxProfile): number {
  const d = profile.deductions;
  const selfLimit =
    profile.ageBand === "below60"
      ? SECTION_80D_SELF_LIMIT
      : SECTION_80D_SELF_SENIOR_LIMIT;
  const parentLimit = d.parentsAreSenior
    ? SECTION_80D_PARENTS_SENIOR_LIMIT
    : SECTION_80D_PARENTS_LIMIT;
  return clamp(d.healthInsuranceSelf, 0, selfLimit) + clamp(d.healthInsuranceParents, 0, parentLimit);
}

function employerNpsAllowed(profile: TaxProfile): number {
  const cap = 0.1 * (profile.salary.basic + profile.salary.da);
  return clamp(profile.salary.employerNps, 0, cap > 0 ? cap : profile.salary.employerNps);
}

function taxOnSlabs(
  income: number,
  slabs: { to: number | null; rate: number }[],
): { tax: number; lines: SlabLine[] } {
  let remaining = Math.max(0, income);
  let lower = 0;
  let tax = 0;
  const lines: SlabLine[] = [];
  for (const slab of slabs) {
    const upper = slab.to ?? Number.POSITIVE_INFINITY;
    const width = Math.max(0, Math.min(remaining, upper - lower));
    const slabTax = width * slab.rate;
    tax += slabTax;
    lines.push({
      from: lower,
      to: slab.to,
      rate: slab.rate,
      tax: slabTax,
    });
    remaining -= width;
    lower = upper;
    if (remaining <= 0) break;
  }
  return { tax, lines };
}

function surcharge(tax: number, taxable: number, regime: Regime): number {
  if (taxable <= 5_000_000) return 0;
  let rate = 0.1;
  if (taxable > 10_000_000) rate = 0.15;
  if (taxable > 20_000_000) rate = regime === "new" ? 0.25 : 0.25;
  if (regime === "old" && taxable > 50_000_000) rate = 0.37;
  if (regime === "new" && taxable > 20_000_000) rate = 0.25;
  return tax * rate;
}

function rebate(tax: number, taxable: number, regime: Regime): number {
  if (regime === "new") {
    if (taxable <= REBATE_NEW_LIMIT) return Math.min(tax, REBATE_NEW_MAX);
    return 0;
  }
  if (taxable <= REBATE_OLD_LIMIT) return Math.min(tax, REBATE_OLD_MAX);
  return 0;
}

function marginalReliefNew(taxAfterRebate: number, taxable: number): number {
  if (taxable <= REBATE_NEW_LIMIT) return taxAfterRebate;
  const excess = taxable - REBATE_NEW_LIMIT;
  return Math.min(taxAfterRebate, excess);
}

export function computeRegime(profile: TaxProfile, regime: Regime): RegimeResult {
  const gross = grossSalary(profile.salary);
  const hra = regime === "old" ? hraExemption(profile) : 0;
  const std = regime === "new" ? STANDARD_DEDUCTION_NEW : STANDARD_DEDUCTION_OLD;
  const pt = Math.min(profile.salary.professionalTax, 2_500);
  const notes: string[] = [];

  let deductionsAllowed = employerNpsAllowed(profile);
  if (employerNpsAllowed(profile) > 0) {
    notes.push("Employer NPS under 80CCD(2) is allowed in both regimes.");
  }

  if (regime === "old") {
    const d80c = section80C(profile.deductions);
    const d80d = section80D(profile);
    const npsExtra = clamp(
      profile.deductions.npsAdditional80CCD1B,
      0,
      SECTION_80CCD1B_LIMIT,
    );
    const homeInterest = clamp(profile.deductions.homeLoanInterest, 0, SECTION_24B_LIMIT);
    const edu = Math.max(0, profile.deductions.educationLoanInterest);
    const tta = clamp(profile.deductions.savingsInterest, 0, SECTION_80TTA_LIMIT);
    const donations = Math.max(0, profile.deductions.donations80G);
    deductionsAllowed += d80c + d80d + npsExtra + homeInterest + edu + tta + donations;
    notes.push("Old regime keeps 80C, 80D, HRA, 24(b), 80E and similar deductions.");
  } else {
    notes.push(
      "New regime is default from Tax Year 2026-27. Most Chapter VI-A deductions (80C, 80D, HRA) are not available.",
    );
    notes.push(
      `Resident individuals with taxable income up to ${REBATE_NEW_LIMIT.toLocaleString("en-IN")} get a rebate (max ${REBATE_NEW_MAX.toLocaleString("en-IN")}), so tax is nil. Salaried people also get a ₹75,000 standard deduction.`,
    );
  }

  const taxable = Math.max(
    0,
    gross -
      hra -
      std -
      pt +
      profile.otherIncome +
      profile.housePropertyLetOut -
      deductionsAllowed,
  );

  const slabs = regime === "new" ? NEW_SLABS : OLD_SLABS[profile.ageBand];
  const { tax, lines } = taxOnSlabs(taxable, slabs);
  const rebateAmt = rebate(tax, taxable, regime);
  let afterRebate = Math.max(0, tax - rebateAmt);
  if (regime === "new") {
    afterRebate = marginalReliefNew(afterRebate, taxable);
  }
  const sur = surcharge(afterRebate, taxable, regime);
  const cess = (afterRebate + sur) * CESS_RATE;
  const totalTax = afterRebate + sur + cess;
  const payableOrRefund = profile.salary.tds - totalTax;

  return {
    regime,
    grossSalary: gross,
    ctc: ctcOf(profile.salary),
    hraExemption: hra,
    standardDeduction: std,
    professionalTax: pt,
    deductionsAllowed,
    taxableIncome: taxable,
    taxBeforeRebate: tax,
    rebate87A: rebateAmt + (tax - rebateAmt - afterRebate),
    taxAfterRebate: afterRebate,
    surcharge: sur,
    cess,
    totalTax,
    tds: profile.salary.tds,
    payableOrRefund,
    slabs: lines,
    notes,
  };
}

export function compareRegimes(profile: TaxProfile): AdvicePack {
  const oldR = computeRegime(profile, "old");
  const newR = computeRegime(profile, "new");
  const recommended: Regime = newR.totalTax <= oldR.totalTax ? "new" : "old";
  const savingsVsOther = Math.abs(oldR.totalTax - newR.totalTax);
  const tips = buildTips(profile, oldR, newR);
  const summary =
    recommended === "new"
      ? `The new regime is cheaper by ₹${Math.round(savingsVsOther).toLocaleString("en-IN")} for this income. New regime is also the legal default.`
      : `The old regime is cheaper by ₹${Math.round(savingsVsOther).toLocaleString("en-IN")} because your deductions (80C, HRA, 80D, housing) outweigh the lower new-regime slabs.`;

  return { old: oldR, new: newR, recommended, savingsVsOther, tips, summary };
}

function taxSavedByExtraOld(
  profile: TaxProfile,
  mutate: (clone: TaxProfile) => void,
): number {
  const base = computeRegime(profile, "old").totalTax;
  const clone: TaxProfile = structuredClone(profile);
  mutate(clone);
  return Math.max(0, base - computeRegime(clone, "old").totalTax);
}

function buildTips(profile: TaxProfile, oldR: RegimeResult, newR: RegimeResult): SavingTip[] {
  const tips: SavingTip[] = [];
  const d = profile.deductions;
  const used80c =
    d.employeePf +
    d.elss +
    d.lifeInsurance +
    d.ppf +
    d.homeLoanPrincipal +
    d.tuitionFees +
    d.other80C +
    d.npsEmployee;
  const leftover80c = Math.max(0, SECTION_80C_LIMIT - used80c);

  if (leftover80c >= 1000) {
    const saved = taxSavedByExtraOld(profile, (c) => {
      c.deductions.elss += leftover80c;
    });
    tips.push({
      id: "80c",
      title: "Finish your Section 80C basket",
      section: "80C",
      regime: "old",
      extraInvestment: leftover80c,
      estimatedTaxSaved: saved,
      detail: `You have used ₹${Math.round(used80c).toLocaleString("en-IN")} of the ₹1.5 lakh 80C limit (EPF already counts). ELSS, PPF, life cover, children’s tuition or home-loan principal can fill the gap. This only helps if you opt for the old regime.`,
      priority: leftover80c > 50_000 ? 95 : 80,
    });
  }

  const leftoverNps = Math.max(0, SECTION_80CCD1B_LIMIT - d.npsAdditional80CCD1B);
  if (leftoverNps >= 1000) {
    const saved = taxSavedByExtraOld(profile, (c) => {
      c.deductions.npsAdditional80CCD1B = SECTION_80CCD1B_LIMIT;
    });
    tips.push({
      id: "nps",
      title: "Use extra NPS under 80CCD(1B)",
      section: "80CCD(1B)",
      regime: "old",
      extraInvestment: leftoverNps,
      estimatedTaxSaved: saved,
      detail: "Up to ₹50,000 in NPS sits on top of 80C. It is one of the last high-conviction old-regime levers after EPF.",
      priority: 88,
    });
  }

  if (d.healthInsuranceSelf < SECTION_80D_SELF_LIMIT) {
    const add = SECTION_80D_SELF_LIMIT - d.healthInsuranceSelf;
    const saved = taxSavedByExtraOld(profile, (c) => {
      c.deductions.healthInsuranceSelf = SECTION_80D_SELF_LIMIT;
    });
    tips.push({
      id: "80d",
      title: "Health cover under Section 80D",
      section: "80D",
      regime: "old",
      extraInvestment: add,
      estimatedTaxSaved: saved,
      detail: "Premiums for self/spouse/children qualify up to ₹25,000 (₹50,000 if you are a senior citizen). Parents have a separate limit.",
      priority: 84,
    });
  }

  if (profile.salary.hraReceived > 0 && d.rentPaid === 0 && profile.livesInRentedHouse) {
    const suggestedRent = Math.round(0.4 * (profile.salary.basic + profile.salary.da));
    tips.push({
      id: "hra",
      title: "Claim HRA with rent receipts",
      section: "10(13A)",
      regime: "old",
      extraInvestment: 0,
      estimatedTaxSaved: taxSavedByExtraOld(profile, (c) => {
        c.deductions.rentPaid = suggestedRent;
        c.livesInRentedHouse = true;
      }),
      detail: "HRA exemption is the least of actual HRA, rent minus 10% of basic+DA, and 50%/40% of basic+DA (metro/non-metro). Keep rent receipts and the landlord PAN if annual rent exceeds ₹1 lakh.",
      priority: 90,
    });
  }

  if (profile.salary.employerNps === 0 && profile.salary.basic > 0) {
    const tenPercent = Math.round(0.1 * (profile.salary.basic + profile.salary.da));
    tips.push({
      id: "nps-employer",
      title: "Ask HR to route 10% of basic to NPS",
      section: "80CCD(2)",
      regime: "both",
      extraInvestment: tenPercent,
      estimatedTaxSaved: Math.max(
        0,
        newR.totalTax -
          computeRegime(
            {
              ...profile,
              salary: { ...profile.salary, employerNps: tenPercent, specialAllowance: Math.max(0, profile.salary.specialAllowance - tenPercent) },
            },
            "new",
          ).totalTax,
      ),
      detail: "Employer NPS (typically 10% of basic + DA for most employers) is deductible in the new regime as well. This is the cleanest CTC restructuring lever after the 2025/2026 slabs.",
      priority: 92,
    });
  }

  if (oldR.totalTax + 1 < newR.totalTax) {
    tips.push({
      id: "regime-old",
      title: "Opt for the old regime at filing",
      section: "115BAC opt-out",
      regime: "old",
      extraInvestment: 0,
      estimatedTaxSaved: newR.totalTax - oldR.totalTax,
      detail: "Salaried taxpayers can choose the regime each year when they file. Your current deductions beat the new-regime slabs.",
      priority: 99,
    });
  } else {
    tips.push({
      id: "regime-new",
      title: "Stay on the new regime (default)",
      section: "Default regime",
      regime: "new",
      extraInvestment: 0,
      estimatedTaxSaved: oldR.totalTax - newR.totalTax,
      detail: "Unless you have large 80C/HRA/housing deductions, the new slabs plus ₹75,000 standard deduction and the ₹12 lakh rebate are usually better.",
      priority: 99,
    });
  }

  if (profile.salary.basic > 0 && profile.salary.hraReceived === 0) {
    tips.push({
      id: "ctc-hra",
      title: "Split CTC into HRA if you pay rent",
      section: "Salary structure",
      regime: "old",
      extraInvestment: 0,
      estimatedTaxSaved: 0,
      detail: "Offer letters that dump everything into basic/special allowance waste HRA. A common structure is ~40% basic, HRA at 40–50% of basic, and the rest as special allowance — then claim rent on the old regime.",
      priority: 70,
    });
  }

  tips.sort((a, b) => b.priority - a.priority);
  return tips;
}

export function mergeProfile(base: TaxProfile, patch: Partial<TaxProfile>): TaxProfile {
  return {
    ...base,
    ...patch,
    salary: { ...base.salary, ...(patch.salary ?? {}) },
    deductions: { ...base.deductions, ...(patch.deductions ?? {}) },
  };
}
