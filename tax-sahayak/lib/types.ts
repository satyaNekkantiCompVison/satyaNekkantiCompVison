export type AgeBand = "below60" | "senior" | "superSenior";
export type Regime = "new" | "old";
export type CityType = "metro" | "nonMetro";
export type DocumentKind = "form16" | "ctc" | "unknown";

export interface SalaryBreakdown {
  basic: number;
  da: number;
  hraReceived: number;
  lta: number;
  specialAllowance: number;
  otherAllowances: number;
  bonus: number;
  employerPf: number;
  employerNps: number;
  gratuity: number;
  professionalTax: number;
  tds: number;
}

export interface DeductionInputs {
  employeePf: number;
  elss: number;
  lifeInsurance: number;
  ppf: number;
  homeLoanPrincipal: number;
  tuitionFees: number;
  other80C: number;
  npsEmployee: number;
  npsAdditional80CCD1B: number;
  healthInsuranceSelf: number;
  healthInsuranceParents: number;
  parentsAreSenior: boolean;
  homeLoanInterest: number;
  rentPaid: number;
  educationLoanInterest: number;
  savingsInterest: number;
  donations80G: number;
}

export interface TaxProfile {
  name: string;
  pan: string;
  employer: string;
  tan: string;
  ageBand: AgeBand;
  city: CityType;
  livesInRentedHouse: boolean;
  fy: string;
  salary: SalaryBreakdown;
  otherIncome: number;
  housePropertyLetOut: number;
  deductions: DeductionInputs;
  sourceText?: string;
  documentKind?: DocumentKind;
}

export interface SlabLine {
  from: number;
  to: number | null;
  rate: number;
  tax: number;
}

export interface RegimeResult {
  regime: Regime;
  grossSalary: number;
  ctc: number;
  hraExemption: number;
  standardDeduction: number;
  professionalTax: number;
  deductionsAllowed: number;
  taxableIncome: number;
  taxBeforeRebate: number;
  rebate87A: number;
  taxAfterRebate: number;
  surcharge: number;
  cess: number;
  totalTax: number;
  tds: number;
  payableOrRefund: number;
  slabs: SlabLine[];
  notes: string[];
}

export interface SavingTip {
  id: string;
  title: string;
  section: string;
  regime: "old" | "new" | "both";
  extraInvestment: number;
  estimatedTaxSaved: number;
  detail: string;
  priority: number;
}

export interface AdvicePack {
  old: RegimeResult;
  new: RegimeResult;
  recommended: Regime;
  savingsVsOther: number;
  tips: SavingTip[];
  summary: string;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}
