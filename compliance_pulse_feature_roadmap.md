# Compliance Pulse — Feature Roadmap (SKU + Lane Focus)

**Date:** 2025-10-25

Architecture Core: **LangGraph v1 | ChromaDB | mem0 | ZenML | FastAPI | Next.js**

---

## 🧩 MVP (Weeks 1 – 4)

**Goal:** Deliver SKU + lane–aware compliance snapshots and weekly digests.

| Category | Feature | Description |
|-----------|----------|-------------|
| **Data & Models** | SKU + Lane Data Model | Define `ClientProfile`, `SkuRef`, `LaneRef`, and `ComplianceEvent`. |
|  | Watchlist Storage | Persist client SKUs and lanes in mem0. |
|  | Basic Normalization | Fetch & normalize HTS, OFAC/CSL, FDA, FSIS, CROSS data. |
| **Pipelines (ZenML)** | `fetch_normalize_index` | Daily ingestion pipeline for SKU/lane data. |
|  | `weekly_pulse` | Weekly diff + summary generator. |
| **Retrieval & Reasoning** | Chroma Collections | Embed policy/ruling text tagged by SKU + lane. |
|  | LangGraph Nodes | Tools: `search_hts`, `screen_parties`, `fetch_refusals`, `find_rulings`. |
|  | Agentic Summaries | Generate “what changed + why it matters” for SKU/lane pairs. |
| **API Layer (FastAPI)** | `/snapshot` | Return single SKU+lane snapshot with citations. |
|  | `/pulse/{client_id}/weekly` | Weekly digest JSON by SKU + lane. |
|  | `/ask` | Ad-hoc reasoning endpoint (“What changed for HTS 8517 China→US lane?”). |
| **UI (Next.js)** | Snapshot Card | 5 tiles (HTS, FTA, Sanctions, Health/Safety, Rulings). |
|  | Weekly Digest View | Displays grouped updates per lane. |
| **Ops & Governance** | API Key Auth | Basic authentication. |
|  | Logging & Metrics | Track latency, coverage, errors. |

✅ **Deliverable:** A fully working MVP producing lane-specific compliance snapshots and automated weekly digests for 10–50 SKUs.

---

## ⚙️ V1 (Weeks 5 – 8)

**Goal:** Add deeper reasoning, personalization, and collaborative delivery.

| Category | Feature | Description |
|-----------|----------|-------------|
| **Memory & Personalization** | Preference Learning | mem0 stores client thresholds (e.g., duty delta ≥ 1%). |
|  | Dismissal Memory | Remember suppressed or false alerts. |
| **Advanced Reasoning** | Change Context Delta | Compare prior week’s data per lane; classify “new”, “resolved”, “escalated”. |
|  | Causal Insights | “Why did this change occur?” (ruling update, tariff revision, refusal trend). |
| **Workflow Automation** | Slack / Email Digest | Send formatted digest summaries automatically. |
|  | CSV / JSON Exports | For BI dashboards or internal tools. |
| **Frontend Enhancements** | Lane Heatmap | Visualize active lanes and risk levels. |
|  | Multi-SKU Compare | Side-by-side view of SKUs on the same lane. |
| **Compliance Coverage** | Add FTA Rules | Pull FTA origin requirements via public datasets. |
|  | Sanctions Delta Tracking | Track changes to restricted party lists over time. |
| **Pipeline Scaling** | ZenML Monitoring | Model-run metrics + alerts on data drift. |
| **Security & Audit** | Audit Trail | Timestamped record of alerts and decisions. |

✅ **Deliverable:** Multi-lane reporting and agentic weekly briefs ready for pilot clients.

---

## 🚀 V2 (Weeks 9 – 16)

**Goal:** Expand intelligence, automation, and multi-tenant scalability.

| Category | Feature | Description |
|-----------|----------|-------------|
| **Predictive Analytics** | Lane Risk Forecasting | Model probability of future duty or sanction risk per lane. |
|  | Trend Detection | Detect patterns of recurring FDA refusals or ruling changes. |
| **Knowledge Graph Expansion** | Graph Integration | Build Neo4j graph linking SKUs, lanes, entities, and regulations. |
|  | Cross-Domain Reasoning | Combine HTS, rulings, and health/safety for compound risk. |
| **Collaboration & UI** | Team Workspaces | Shared dashboards + role-based access. |
|  | Commenting & Notes | Threaded discussions per SKU/lane event. |
| **APIs & Integrations** | Webhooks | Send real-time alerts to ERP or TMS systems. |
|  | Partner Integrations | Plug-ins for Magaya, CargoWise, or Project44. |
| **Operational Scaling** | Multi-Tenant DB | Namespace data by organization. |
|  | CI/CD Pipeline | Automated tests + deployment via ZenML or GitHub Actions. |
| **UX Innovation** | “Explain This Change” | Inline chat powered by LangGraph reasoner with citations. |
|  | “Compliance Pulse GPT” | Summarized chat mode for ops teams to ask daily questions. |

✅ **Deliverable:** Production-ready, multi-tenant SaaS with predictive lane intelligence and agentic ops assistant.

---

## 📊 Metrics Evolution

| Stage | Core KPIs |
|--------|-----------|
| **MVP** | Snapshot latency, SKU coverage, data accuracy |
| **V1** | Digest engagement rate, alert precision (%) |
| **V2** | Predictive risk score accuracy, user retention (%), multi-tenant uptime |
