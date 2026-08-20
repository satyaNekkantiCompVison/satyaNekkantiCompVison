import { defaultProfile, emptyDeductions, emptySalary } from "./taxEngine";
import type { DocumentKind, TaxProfile } from "./types";
import { num } from "./money";

function pick(text: string, patterns: RegExp[]): number {
  for (const pattern of patterns) {
    const match = text.match(pattern);
    if (match?.[1]) {
      const value = num(match[1]);
      if (value > 0) return value;
    }
  }
  return 0;
}

function pickStr(text: string, patterns: RegExp[]): string {
  for (const pattern of patterns) {
    const match = text.match(pattern);
    if (match?.[1]) return match[1].trim();
  }
  return "";
}

function detectKind(text: string): DocumentKind {
  const t = text.toLowerCase();
  if (
    t.includes("form 16") ||
    t.includes("form16") ||
    t.includes("certificate under section 203") ||
    t.includes("part b of form no. 16")
  ) {
    return "form16";
  }
  if (
    t.includes("cost to company") ||
    t.includes("ctc") ||
    t.includes("offer letter") ||
    t.includes("compensation") ||
    t.includes("fixed pay")
  ) {
    return "ctc";
  }
  return "unknown";
}

function annualizeIfMonthly(value: number, text: string, labelHint: string): number {
  if (value <= 0) return 0;
  const around = new RegExp(`.{0,40}${labelHint}.{0,80}`, "i");
  const window = text.match(around)?.[0] ?? text;
  const looksMonthly =
    /per\s*month|\/\s*month|monthly|p\.m\.|pm\b/i.test(window) &&
    value < 400_000;
  return looksMonthly ? value * 12 : value;
}

export function parseTaxDocument(raw: string): TaxProfile {
  const text = raw.replace(/\u00a0/g, " ").replace(/[ \t]+/g, " ");
  const kind = detectKind(text);
  const profile = defaultProfile();
  profile.sourceText = raw.slice(0, 20_000);
  profile.documentKind = kind;

  profile.name = pickStr(text, [
    /Name of Employee\s*[:\-]\s*([A-Za-z .]+)/i,
    /Employee Name\s*[:\-]\s*([A-Za-z .]+)/i,
    /Dear\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)+)/,
  ]);
  profile.pan = pickStr(text, [
    /\bPAN\b\s*[:\-]\s*([A-Z]{5}[0-9]{4}[A-Z])/i,
    /\b([A-Z]{5}[0-9]{4}[A-Z])\b/,
  ]).toUpperCase();
  profile.employer = pickStr(text, [
    /Name and address of the Employer[\s\S]{0,40}?([A-Za-z0-9 .,&]+(?:Pvt|Private|Ltd|Limited|Inc|LLP)[A-Za-z0-9 .,&]*)/i,
    /Employer\s*[:\-]\s*([A-Za-z0-9 .,&]+)/i,
    /Company\s*[:\-]\s*([A-Za-z0-9 .,&]+)/i,
  ]);
  profile.tan = pickStr(text, [/\bTAN\b\s*[:\-]\s*([A-Z]{4}[0-9]{5}[A-Z])/i]).toUpperCase();

  const salary = emptySalary();
  salary.basic = annualizeIfMonthly(
    pick(text, [
      /Basic(?:\s*Salary)?\s*[:\-]?\s*(?:INR|Rs\.?|₹)?\s*([\d,]+)/i,
      /Basic Pay\s*[:\-]?\s*(?:INR|Rs\.?|₹)?\s*([\d,]+)/i,
    ]),
    text,
    "Basic",
  );
  salary.da = annualizeIfMonthly(
    pick(text, [
      /Dearness Allowance\s*[:\-]?\s*(?:INR|Rs\.?|₹)?\s*([\d,]+)/i,
      /\bDA\b\s*[:\-]?\s*(?:INR|Rs\.?|₹)?\s*([\d,]+)/i,
    ]),
    text,
    "Dearness",
  );
  salary.hraReceived = annualizeIfMonthly(
    pick(text, [
      /House Rent Allowance\s*[:\-]?\s*(?:INR|Rs\.?|₹)?\s*([\d,]+)/i,
      /\bHRA\b\s*[:\-]?\s*(?:INR|Rs\.?|₹)?\s*([\d,]+)/i,
    ]),
    text,
    "HRA",
  );
  salary.lta = annualizeIfMonthly(
    pick(text, [
      /Leave Travel (?:Allowance|Assistance)\s*[:\-]?\s*(?:INR|Rs\.?|₹)?\s*([\d,]+)/i,
      /\bLTA\b\s*[:\-]?\s*(?:INR|Rs\.?|₹)?\s*([\d,]+)/i,
    ]),
    text,
    "LTA",
  );
  salary.specialAllowance = annualizeIfMonthly(
    pick(text, [
      /Special Allowance\s*[:\-]?\s*(?:INR|Rs\.?|₹)?\s*([\d,]+)/i,
    ]),
    text,
    "Special Allowance",
  );
  salary.otherAllowances = annualizeIfMonthly(
    pick(text, [
      /Other Allowance[s]?\s*[:\-]?\s*(?:INR|Rs\.?|₹)?\s*([\d,]+)/i,
      /Conveyance Allowance\s*[:\-]?\s*(?:INR|Rs\.?|₹)?\s*([\d,]+)/i,
    ]),
    text,
    "Other Allowance",
  );
  salary.bonus = pick(text, [
    /(?:Performance )?(?:Bonus|Variable Pay|Incentive)\s*[:\-]?\s*(?:INR|Rs\.?|₹)?\s*([\d,]+)/i,
  ]);
  salary.employerPf = annualizeIfMonthly(
    pick(text, [
      /Employer(?:'s)?\s*(?:PF|Provident Fund)\s*[:\-]?\s*(?:INR|Rs\.?|₹)?\s*([\d,]+)/i,
      /PF \(Employer\)\s*[:\-]?\s*(?:INR|Rs\.?|₹)?\s*([\d,]+)/i,
    ]),
    text,
    "Employer PF",
  );
  salary.employerNps = annualizeIfMonthly(
    pick(text, [
      /Employer(?:'s)?\s*NPS\s*[:\-]?\s*(?:INR|Rs\.?|₹)?\s*([\d,]+)/i,
      /NPS \(Employer\)\s*[:\-]?\s*(?:INR|Rs\.?|₹)?\s*([\d,]+)/i,
    ]),
    text,
    "Employer NPS",
  );
  salary.gratuity = pick(text, [
    /Gratuity\s*[:\-]?\s*(?:INR|Rs\.?|₹)?\s*([\d,]+)/i,
  ]);
  salary.professionalTax = pick(text, [
    /Professional Tax\s*[:\-]?\s*(?:INR|Rs\.?|₹)?\s*([\d,]+)/i,
    /\bPT\b\s*[:\-]?\s*(?:INR|Rs\.?|₹)?\s*([\d,]+)/i,
  ]);
  salary.tds = pick(text, [
    /Tax Deducted at Source\s*[:\-]?\s*(?:INR|Rs\.?|₹)?\s*([\d,]+(?:\.\d+)?)/i,
    /\bTDS\b\s*[:\-]?\s*(?:INR|Rs\.?|₹)?\s*([\d,]+)/i,
    /Total tax deducted\s*[:\-]?\s*(?:INR|Rs\.?|₹)?\s*([\d,]+)/i,
  ]);

  const grossFromDoc = pick(text, [
    /Gross Salary\s*[:\-]?\s*(?:INR|Rs\.?|₹)?\s*([\d,]+)/i,
    /Gross(?:\s*Total)?\s*Income\s*[:\-]?\s*(?:INR|Rs\.?|₹)?\s*([\d,]+)/i,
    /Total CTC\s*[:\-]?\s*(?:INR|Rs\.?|₹)?\s*([\d,]+)/i,
    /Cost to Company\s*[:\-]?\s*(?:INR|Rs\.?|₹)?\s*([\d,]+)/i,
    /Annual CTC\s*[:\-]?\s*(?:INR|Rs\.?|₹)?\s*([\d,]+)/i,
  ]);

  const computedGross =
    salary.basic +
    salary.da +
    salary.hraReceived +
    salary.lta +
    salary.specialAllowance +
    salary.otherAllowances +
    salary.bonus;

  if (computedGross === 0 && grossFromDoc > 0) {
    salary.basic = Math.round(grossFromDoc * 0.4);
    salary.hraReceived = Math.round(grossFromDoc * 0.2);
    salary.specialAllowance = grossFromDoc - salary.basic - salary.hraReceived;
  } else if (computedGross > 0 && salary.specialAllowance === 0 && grossFromDoc > computedGross) {
    salary.specialAllowance = grossFromDoc - computedGross;
  }

  const deductions = emptyDeductions();
  deductions.employeePf = annualizeIfMonthly(
    pick(text, [
      /Employee(?:'s)?\s*(?:PF|Provident Fund)\s*[:\-]?\s*(?:INR|Rs\.?|₹)?\s*([\d,]+)/i,
      /PF \(Employee\)\s*[:\-]?\s*(?:INR|Rs\.?|₹)?\s*([\d,]+)/i,
    ]),
    text,
    "Employee PF",
  );
  if (deductions.employeePf === 0 && salary.employerPf > 0) {
    deductions.employeePf = salary.employerPf;
  }
  deductions.elss = pick(text, [/ELSS\s*[:\-]?\s*(?:INR|Rs\.?|₹)?\s*([\d,]+)/i]);
  deductions.lifeInsurance = pick(text, [
    /Life Insurance(?: Premium)?\s*[:\-]?\s*(?:INR|Rs\.?|₹)?\s*([\d,]+)/i,
    /LIC\s*[:\-]?\s*(?:INR|Rs\.?|₹)?\s*([\d,]+)/i,
  ]);
  deductions.ppf = pick(text, [/\bPPF\b\s*[:\-]?\s*(?:INR|Rs\.?|₹)?\s*([\d,]+)/i]);
  deductions.npsEmployee = pick(text, [
    /NPS \(Employee\)\s*[:\-]?\s*(?:INR|Rs\.?|₹)?\s*([\d,]+)/i,
    /Employee NPS\s*[:\-]?\s*(?:INR|Rs\.?|₹)?\s*([\d,]+)/i,
  ]);
  deductions.npsAdditional80CCD1B = pick(text, [
    /80CCD\(1B\)\s*[:\-]?\s*(?:INR|Rs\.?|₹)?\s*([\d,]+)/i,
  ]);
  deductions.healthInsuranceSelf = pick(text, [
    /(?:Health|Medical) Insurance\s*[:\-]?\s*(?:INR|Rs\.?|₹)?\s*([\d,]+)/i,
    /Section 80D\s*[:\-]?\s*(?:INR|Rs\.?|₹)?\s*([\d,]+)/i,
  ]);
  deductions.rentPaid = annualizeIfMonthly(
    pick(text, [
      /Rent Paid\s*[:\-]?\s*(?:INR|Rs\.?|₹)?\s*([\d,]+)/i,
      /Annual Rent\s*[:\-]?\s*(?:INR|Rs\.?|₹)?\s*([\d,]+)/i,
    ]),
    text,
    "Rent",
  );
  deductions.homeLoanInterest = pick(text, [
    /Home Loan Interest\s*[:\-]?\s*(?:INR|Rs\.?|₹)?\s*([\d,]+)/i,
    /Interest on housing loan\s*[:\-]?\s*(?:INR|Rs\.?|₹)?\s*([\d,]+)/i,
    /Section 24[b]?\s*[:\-]?\s*(?:INR|Rs\.?|₹)?\s*([\d,]+)/i,
  ]);
  deductions.homeLoanPrincipal = pick(text, [
    /Home Loan Principal\s*[:\-]?\s*(?:INR|Rs\.?|₹)?\s*([\d,]+)/i,
  ]);

  const section80cTotal = pick(text, [
    /Deduction under section 80C\s*[:\-]?\s*(?:INR|Rs\.?|₹)?\s*([\d,]+)/i,
    /Section 80C\s*[:\-]?\s*(?:INR|Rs\.?|₹)?\s*([\d,]+)/i,
  ]);
  const accounted80c =
    deductions.employeePf +
    deductions.elss +
    deductions.lifeInsurance +
    deductions.ppf +
    deductions.homeLoanPrincipal +
    deductions.npsEmployee;
  if (section80cTotal > accounted80c) {
    deductions.other80C = section80cTotal - accounted80c;
  }

  if (/non[-\s]?metro|tier\s*2|bengaluru|pune|hyderabad|chennai/i.test(text) && !/mumbai|delhi|kolkata|chennai metro/i.test(text)) {
    // Chennai is metro for HRA. Keep metro default unless clearly non-metro.
  }
  if (/mumbai|delhi|kolkata|chennai/i.test(text)) {
    profile.city = "metro";
  } else if (/non[-\s]?metro/i.test(text)) {
    profile.city = "nonMetro";
  }

  profile.salary = salary;
  profile.deductions = deductions;
  return profile;
}
