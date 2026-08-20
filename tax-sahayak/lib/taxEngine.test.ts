import { describe, expect, it } from "vitest";
import { compareRegimes, computeRegime, defaultProfile, hraExemption } from "../lib/taxEngine";
import { parseTaxDocument } from "../lib/parseDocument";
import { answerChat } from "../lib/chatbot";

describe("new regime Tax Year 2026-27", () => {
  it("makes salaried income of 12.75L tax-free after standard deduction and rebate", () => {
    const profile = defaultProfile();
    profile.salary.basic = 800_000;
    profile.salary.specialAllowance = 475_000;
    const result = computeRegime(profile, "new");
    expect(result.standardDeduction).toBe(75_000);
    expect(result.taxableIncome).toBe(1_200_000);
    expect(result.totalTax).toBe(0);
  });

  it("charges tax above the 12L rebate window", () => {
    const profile = defaultProfile();
    profile.salary.basic = 1_000_000;
    profile.salary.specialAllowance = 575_000;
    const result = computeRegime(profile, "new");
    expect(result.taxableIncome).toBe(1_500_000);
    expect(result.totalTax).toBeGreaterThan(50_000);
  });
});

describe("old regime", () => {
  it("computes HRA exemption as the least of the three tests", () => {
    const profile = defaultProfile();
    profile.city = "metro";
    profile.livesInRentedHouse = true;
    profile.salary.basic = 600_000;
    profile.salary.hraReceived = 300_000;
    profile.deductions.rentPaid = 360_000;
    expect(hraExemption(profile)).toBe(300_000);
  });

  it("beats the new regime when 80C, HRA and 80D are large", () => {
    const profile = defaultProfile();
    profile.salary.basic = 1_200_000;
    profile.salary.hraReceived = 600_000;
    profile.salary.specialAllowance = 700_000;
    profile.deductions.employeePf = 144_000;
    profile.deductions.elss = 6_000;
    profile.deductions.healthInsuranceSelf = 25_000;
    profile.deductions.rentPaid = 720_000;
    profile.deductions.npsAdditional80CCD1B = 50_000;
    profile.deductions.homeLoanInterest = 200_000;
    const pack = compareRegimes(profile);
    expect(pack.recommended).toBe("old");
    expect(pack.old.totalTax).toBeLessThan(pack.new.totalTax);
  });
});

describe("document parser", () => {
  it("reads a Form 16 style text dump", () => {
    const text = `
      Form 16
      Certificate under section 203
      Name of Employee: Anita Sharma
      PAN: ABCDE1234F
      TAN: MUMD12345E
      Gross Salary: 1800000
      Basic Salary: 720000
      House Rent Allowance: 360000
      Special Allowance: 720000
      Employee PF: 86400
      Professional Tax: 2400
      Tax Deducted at Source: 185000
      Rent Paid: 300000
    `;
    const parsed = parseTaxDocument(text);
    expect(parsed.documentKind).toBe("form16");
    expect(parsed.pan).toBe("ABCDE1234F");
    expect(parsed.salary.basic).toBe(720_000);
    expect(parsed.salary.hraReceived).toBe(360_000);
    expect(parsed.deductions.employeePf).toBe(86_400);
    expect(parsed.salary.tds).toBe(185_000);
  });

  it("annualises monthly CTC lines", () => {
    const text = `
      Offer Letter — Cost to Company
      Annual CTC: 2400000
      Basic per month: 80000
      HRA per month: 40000
      Special Allowance per month: 60000
      Employer PF per month: 9600
    `;
    const parsed = parseTaxDocument(text);
    expect(parsed.documentKind).toBe("ctc");
    expect(parsed.salary.basic).toBe(960_000);
    expect(parsed.salary.hraReceived).toBe(480_000);
  });
});

describe("chatbot", () => {
  it("explains slabs without a profile", () => {
    const reply = answerChat("What are the new regime slabs?", [], defaultProfile());
    expect(reply).toMatch(/4–8L 5%/);
    expect(reply).toMatch(/12 lakh/i);
  });
});
