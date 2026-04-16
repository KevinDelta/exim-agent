# Compliance Pulse Data Plan

Purpose: Define what we capture from client users today and what we must add to deliver a reliable, action‑oriented
compliance pulse for U.S. exports to Nigeria (grounded in the construction parts example), extendable to other lanes.

Scope and assumptions
- Focus: Non-ITAR construction equipment parts, EAR99/NLR expected; buyer is a small Nigerian company; Incoterms FOB.
- Source: Based on our weekly brief and the Notes (Form M, PAAR, SONCAP, screening, AES, FCPA risks).
- Goal: Make shipment readiness, risk, and document status observable with clear go/no-go gates and alerts.

## 1) Data We Collect Today vs. What We Need Next

Below, “Today” reflects our current intake patterns for the working Nigeria brief. “Next” lists fields to enable
automation, risk decisions, and auditable records. Examples are realistic market values for clarity.

### A. Parties, Ownership, and Roles
- Today (baseline)
  - Exporter legal entity (name, US address)
  - Buyer name, country (e.g., “NgBuyer Ltd.”, Nigeria)
  - Freight forwarder (if provided), role (buyer- or seller-nominated)
- Next (to add)
  - Full party registry details: company number (e.g., CAC RC/BN), address, contacts (name, email), website
  - Role mapping: Seller, Buyer, Consignee, Notify, FF, Customs Broker, Bank(s)
  - Beneficial ownership declaration (shareholders ≥25%), org chart or UBO IDs
  - Screening context: country of registration, operating countries, bank SWIFT/BIC, known intermediaries
  - FCPA risk signals: presence of government ties, PEP flags (Y/N/Unknown), adverse media summary

### B. Items and Classification
- Today (baseline)
  - Item descriptions, quantities, unit price, extended value (e.g., bucket teeth 500 pcs x $18)
  - HS/HTS candidate codes (e.g., 8431.49, 8413.60) — often draft
- Next (to add)
  - Final HS codes with confidence score + source (broker, ruling, internal memo)
  - Export control status per line: ECCN or EAR99; reasons for control (if ECCN), license basis (NLR/Exception/License)
  - Country of origin per line and marking status
  - Schedule B code (for AES), units of measure (UOM) and schema alignment
  - Technical attributes that affect control: power, encryption, pressure rating, military applicability (Y/N)
  - Packaging linkage: which crate/pallet contains which SKU and count

### C. Commercial Terms and Values
- Today (baseline)
  - Incoterms rule + place (e.g., FOB Houston), currency (USD), total commercial value
- Next (to add)
  - Payment terms (LC/advance/open), bank names, LC number (if any), LC conditions
  - Discounts/surcharges lines; freight and insurance values (if applicable) to compute CIF for buyer-side taxes
  - E‑invoicing/e‑valuation alignment: declared unit price vs. portal benchmarks (Nigeria specific)

### D. Logistics and Operations
- Today (baseline)
  - Origin city/state, intended load port (e.g., Houston Barbours Cut), destination port (Apapa/Tin Can)
  - Packaging summary: crate/pallet count, gross weight, CBM (e.g., 5.2 CBM, 3,156 kg)
- Next (to add)
  - Mode and service: LCL/FCL, carrier (or buyer-nominated), target vessel/voyage/ETD/ETA
  - Dimensional detail per package: L×W×H cm, net/gross weight kg, ISPM‑15 status, seal numbers
  - Handover milestones: warehouse ready date, gate‑in, on‑board date, transshipment ports
  - Risk controls: photo set at pack/load, GPS‑logged pickup, high‑security trucking requested (Y/N)

### E. U.S. Export Steps
- Today (baseline)
  - Assumed NLR; end‑use/end‑user review prompt
- Next (to add)
  - End‑Use/End‑User Statement (EUS) captured and signed (file + metadata: signer, date)
  - AES/EEI filing per Schedule B line; ITN number; filer (self/FF); filing timestamp
  - Shipper’s Letter of Instruction (SLI) versioned; forwarder acknowledgement
  - Red‑flag checks: returns, reexports, military/security use; escalation disposition

### F. Nigeria Import Controls (Buyer‑Side, we track as dependencies)
- Today (baseline)
  - Reminder that Form M/PAAR/SONCAP may apply
- Next (to add)
  - Form M: bank, number, open date, status, HS lines, invoice reference, validity
  - PAAR: number, issue date, value/HS alignment status, discrepancies (Y/N + notes)
  - SONCAP path: Regulated (PC/SC details) or Exemption (industrial spares letter); certificate numbers and dates
  - Other regulator approvals (if applicable): NCC, NAFDAC, NADDC, NERC; reference numbers, scope

### G. Screening, AML, and Banks
- Today (baseline)
  - Basic party screening request
- Next (to add)
  - Lists screened: OFAC SDN/NS‑MPI, BIS Entity/MEU/UVL, UN, EU, UK HMT; banks screened; results + false positive notes
  - Screening cadence: quote, pre‑ship, pre‑release, pre‑payment; timestamps and auditor trail
  - Ownership screening (OFAC 50% rule) outcome; PEP/adverse media summaries (brief text + link)

### H. Payments and FX
- Today (baseline)
  - Currency and nominal terms
- Next (to add)
  - Payment instrument: LC (confirmed/unconfirmed), TT advance, escrow; issuing/confirming bank SWIFT
  - Sanctions/AML flags on banks; expected payment date; proof of funds or LC issuance evidence
  - CBN e‑Invoice/e‑Valuation linkage ID (if available to buyer), variance flags (Y/N)

### I. Documents and Artifacts
- Today (baseline)
  - Commercial invoice and packing list placeholders
- Next (to add)
  - Versioned documents: invoice, packing list, COO, insurance cert, SLI, B/L or AWB, photos, crate maps
  - Nigeria docs: Form M, PAAR, SONCAP PC/SC or exemption letter
  - Audit metadata: file hash, uploaded by, timestamp; cross‑refs to shipment ID and line items

### J. Human Rights and Misuse
- Today (baseline)
  - End‑use attestation prompt
- Next (to add)
  - Contract clauses: no military/security use, no diversion, audit rights (Y/N with clause text ID)
  - Red‑flag catalog: indicators present (Y/N) + mitigation actions; go/no‑go decision with approver ID

## 2) Derived Outputs and “Pulse” Signals

What the platform should calculate and surface once the above fields are present.

- Shipment readiness score
  - Gate checks: EUS signed, AES filed/ITN present, Form M open, SONCAP path selected, screening clean/cleared
  - Blockers vs. warnings: blockers prevent “Ready to Ship”; warnings require acknowledgment

- Nigeria importability snapshot (buyer‑side)
  - Duty/VAT/levies estimate by HS (5–10% duty bands typical for parts; VAT 7.5%, ETLS 0.5%, CISS 1%)
  - Status of Form M → PAAR → SONCAP artifacts; variance between invoice/Form M/PAAR

- Screening pulse
  - Next refresh due, last lists used, hit summary, ownership screen result, adverse media notes

- Document completeness
  - Required docs per incoterm and mode; missing items; last version timestamp; hash for audit

- Operational risk pulse
  - Port congestion outlook (Apapa/Tin Can), dwell time risk, security controls (implemented Y/N)

## 3) Validation Rules and Conditional Logic

- Conditional requirements
  - If Incoterms FOB → seller must complete AES and provide SLI; buyer handles Form M/PAAR/SONCAP (we still track IDs)
  - If HS indicates SON regulation → require SONCAP PC before SC; else capture exemption letter
  - Any military/security end‑use signal → escalate; license determination required, shipping blocked

- Field validations
  - HS code format (6–10 digits), Schedule B/UOM alignment, currency ISO 4217, country ISO 3166‑1 alpha‑2
  - Dates in ISO 8601; numbers with decimal scale; file size/type limits for uploads
  - Names/addresses required for all parties; SWIFT/BIC for banks if provided

## 4) Data Model Sketch (JSON‑like, abbreviated)

```json
{
  "shipment_id": "EX-1115-NG-01",
  "incoterms": {"rule": "FOB", "place": "Houston, US"},
  "parties": {
    "exporter": {"name": "USCo Inc.", "address": "Dallas, TX"},
    "buyer": {"name": "NgBuyer Ltd.", "country": "NG", "cac_number": "RC123456"},
    "consignee": {"name": "NgBuyer Lagos", "address": "Lagos"},
    "forwarder": {"name": "Buyer‑nominated", "role": "FF"}
  },
  "items": [
    {"desc": "Bucket teeth", "qty": 500, "unit_price": 18, "hs": "843149", "eccn": "EAR99", "origin": "US"},
    {"desc": "Hydraulic gear pump", "qty": 12, "unit_price": 420, "hs": "841360", "eccn": "EAR99", "origin": "US"}
  ],
  "us_export": {"eus_signed": true, "aes": {"itn": "X2025ABC123", "filed_at": "2025-11-18T19:20:00Z"}},
  "ng_import": {"form_m": {"number": "FM12345", "status": "OPEN"}, "soncap": {"path": "PC_SC", "pc": "PC98765"}},
  "screening": {"status": "CLEARED", "last_refresh": "2025-11-18"},
  "docs": {"invoice": {"version": 2, "hash": "..."}, "packing_list": {"version": 1, "hash": "..."}}
}
```

## 5) UX Flow and Timing (Milestones)

- Quote/Onboarding
  - Parties, basic items, destination, incoterms, end‑use intent, screening v1
- Pre‑Shipment (T‑7 to T‑3)
  - Final HS/ECCN, packaging/dimensions, EUS signed, AES planned, buyer opens Form M/chooses SONCAP path
- Ready to Ship (T‑1)
  - AES filed (ITN), invoice/packing list finalized, photo evidence, crate map; risk pulse green or amber (no reds)
- Post‑Departure
  - B/L upload, screening refresh, Nigeria artifact tracking (PAAR issued, SONCAP certificates), exceptions log

## 6) KPIs and Alerts

- KPIs
  - % shipments with all blockers cleared before gate‑in
  - Avg. time from Form M open → PAAR issue; % SONCAP certificates obtained pre‑arrival
  - % screenings with hits cleared < 24h; % invoices within e‑valuation tolerance

- Alerts
  - Blockers: No EUS, no AES/ITN, no Form M, no SONCAP path, open screening hits, end‑use escalation open
  - Warnings: Invoice/Form M variance, missing crate photos, missing seal numbers, bank screening pending

## 7) Implementation Phases

- Phase 0 (Now)
  - Lock “Today” fields in intake; add minimal IDs for Form M/SONCAP and AES ITN; enable manual status capture

- Phase 1 (Next 2–4 weeks)
  - Add ownership/UBO capture, screening cadence with audit trail, document versioning + hashes, package‑level details
  - Conditional gates for blockers; readiness scorecard on shipment page

- Phase 2 (4–8 weeks)
  - Nigeria calculators (duty/VAT/levies ranges), e‑valuation variance flagging, SONCAP workflow templates
  - API hooks for screeners; bank/LC metadata forms; port‑risk signals surfaced in pulse

## 8) Privacy, Security, and Audit

- Do not store raw IDs beyond necessity; mask sensitive bank details; redact PII in logs
- Retention: shipment docs retained per policy; screening logs immutable with timestamps and decision owner
- Access control: limit UBO and bank data to compliance roles; exportable audit bundle per shipment

---

Action: Adopt the “Next” fields per section, implement blocker gates, and expose a single pulse widget that summarizes
readiness, screening status, and Nigeria artifact progress. This enables clear go/no‑go calls and faster exception
handling for client users.

