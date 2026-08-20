# Sahayak Tax

ClearTax-style **India ITR prep** for Tax Year **2026-27**, plus a chatbot that reads Form 16 / CTC offer letters and suggests savings under Indian tax law.

This is a planning workspace. It does **not** e-file on the Income Tax Department portal.

## Features

- ITR-1 style filing wizard (identity, salary, deductions, regime, demo acknowledgement)
- Old vs new regime calculator (Budget 2025 slabs retained in Budget 2026)
- Upload Form 16 or CTC (PDF / text) with annualisation of monthly CTC lines
- Savings bot: 80C, HRA, 80D, NPS 80CCD(1B) & employer 80CCD(2), CTC split
- Sample documents in `public/samples/`

## Run

```bash
cd tax-sahayak
npm install
npm test
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

## Law notes (engine)

- New regime default: 0–4L nil, then 5/10/15/20/25/30% up to 24L+
- Rebate: taxable income ≤ ₹12 lakh → tax nil (max ₹60,000), plus marginal relief
- Standard deduction: ₹75,000 new / ₹50,000 old
- 4% health & education cess
- Old regime keeps HRA, 80C (₹1.5L), 80CCD(1B) ₹50k, 80D, 24(b) ₹2L
- Employer NPS 80CCD(2) allowed in both regimes
