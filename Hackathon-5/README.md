# The HVAC Margin Rescue Challenge
## Hackathon — Build an AI Agent (5-6 Hours)

---

## The Scenario

You're the CFO of a $50M/year commercial HVAC contractor.

Last quarter, three projects closed out at **6.8% realized margin** against a **15.2% bid margin**. This isn't an anomaly — it's the pattern. By the time your team notices margin erosion, it's too late to recover.

Dashboards show you data. **You need something that thinks.**

An agent doesn't wait to be asked. It reasons through your portfolio, decides what matters, takes action, and reports back — autonomously.

---

## What Makes an Agent

An AI agent is a system that can **reason, plan, use tools, and loop** until a goal is complete.

| Component | Role |
|-----------|------|
| **LLM (Brain)** | Understands goals, reasons about data, decides next steps |
| **Tools** | Functions the agent can call: data queries, calculations, document generation |
| **Memory** | Retains context across the analysis so it doesn't repeat work |
| **Autonomy Loop** | Continues investigating until the picture is complete — not after one query |

The difference between a chatbot and an agent: a chatbot answers a question. An agent pursues a goal.

---

## Your Mission

Build an AI agent that **autonomously protects margin** across a portfolio of HVAC construction projects.

Given a single prompt like *"How's my portfolio doing?"*, your agent should:

1. **Scan** the full portfolio and assess margin health across all projects
2. **Investigate** — when it finds something wrong, dig deeper using available data
3. **Act** — produce specific, actionable outputs (not just "risk detected")
4. **Converse** — support follow-up questions using context from its prior analysis

How you architect the tools, what signals you search for, and how deep the agent investigates is up to you.

---

## The Dataset

### Data Files

| File | Description |
|------|-------------|
| `contracts.csv` | Base contract information |
| `sov.csv` | Schedule of Values (line-item breakdown per project) |
| `sov_budget.csv` | Original bid estimates for variance analysis |
| `labor_logs.csv` | Daily crew time entries (~16K records) |
| `material_deliveries.csv` | Material receipts |
| `billing_history.csv` | Pay application headers |
| `billing_line_items.csv` | Pay application line details |
| `change_orders.csv` | Change orders (various approval states) |
| `rfis.csv` | Requests for Information |
| `field_notes.csv` | ~1,300 unstructured daily field reports |

The dataset contains realistic embedded signals — scope drift, verbal approvals, labor overruns, billing lags, and pending change orders. Not every project is in trouble, and not every signal is obvious. **Your agent needs to find the story in the data.**

### Domain Primer

- **SOV (Schedule of Values):** The contract broken into billable line items by work type
- **Burden Rate:** Multiplier on labor (taxes, insurance, benefits) — typically 1.35–1.55x
- **Labor Cost:** `(straight_time_hrs + overtime_hrs × 1.5) × hourly_rate × burden_multiplier`
- **Change Order:** Formal request to modify scope/cost (can be approved, pending, or rejected)
- **RFI:** Request for Information — can carry hidden cost exposure
- **Billing Lag:** Gap between work completed and amounts billed

---

## Technical Requirements

### Required Stack
- **v0** (v0.dev) for UI scaffolding — either via chat or IDE integration
- **Vercel AI SDK** (`ai` package) for agent orchestration
- **Granola** — you must use Granola for prompting the agent (e.g., defining goals, instructions, or agent behavior)
- **Email capability** — the agent must be able to send you an email (e.g., to report findings, alerts, or portfolio summaries)
- **Deployment** to Vercel (strongly encouraged)

### Key AI SDK Concepts

The Vercel AI SDK provides the building blocks for agent behavior:

- **Tool definitions** — functions the LLM can decide to call
- **`stopWhen: stepCountIs(N)`** — lets the agent loop autonomously for up to N steps
- **`onStepFinish`** — hook into each agent step for logging or UI updates
- **Streaming** — `streamText()` for real-time agent responses

How you design your tools, what data they access, and how many steps you allow is a core design decision.

### Recommended Stack
- Next.js 14+ (App Router)
- Shadcn/ui
- OpenAI, Anthropic, or similar LLM provider
- Recharts (optional, for any visual components)

---

## Evaluation Criteria (100 points)

### Agent Intelligence — 40 pts
- Does the agent reason autonomously across the portfolio?
- Does it chain multiple tool calls to investigate root causes?
- Are its calculations accurate?
- Does it produce **actionable outputs** — not just observations?

### Agent Experience — 30 pts
- Can you see what the agent is doing as it works? (transparency)
- Does it support conversational follow-up with memory of prior analysis?
- Are responses streamed in real-time?
- Does it communicate in plain English, not technical jargon?

### Implementation Quality — 20 pts
- Built with v0 + Vercel AI SDK
- Uses Granola for prompting the agent
- Agent can send you an email (e.g., report, alert, or summary)
- Handles the full dataset efficiently (~18K records)
- Responds within a reasonable timeframe
- Deployed and accessible

### Business Insight — 10 pts
- Does the agent explain *why* problems exist, not just flag them?
- Can it forecast outcomes or quantify recovery potential?

### Bonus (up to +20 pts)
- Proactive alerting without being prompted
- Cross-project pattern recognition
- Confidence levels and uncertainty acknowledgment
- Deep multi-turn conversational memory

---

## Deliverables

1. **Working Agent** — GitHub repo or deployed URL with README
2. **v0 Proof** — Project link or IDE prompt history
3. **Technical Summary (1 page)** — Architecture, tool design, model strategy, and what you'd improve

**Submit your project:** [Pulse AI NYC Hackathon — Devpost](https://pulse-ai-nyc-hackathon-hvac.devpost.com/)

---

## What NOT to Build

- **A static dashboard** — charts without reasoning
- **A chatbot** — something that only answers when asked
- **A data pipeline** — load CSVs directly, don't build ETL
- **A black box** — if the user can't see the agent thinking, it's not an agent

---

---

## Resources

- [Vercel AI SDK — Building Agents](https://sdk.vercel.ai/docs/agents/building-agents)
- [Vercel AI SDK — Tools](https://sdk.vercel.ai/docs/ai-sdk-core/tools-and-tool-calling)
- [Vercel AI SDK — Loop Control](https://sdk.vercel.ai/docs/agents/loop-control)
- [v0 Docs](https://v0.dev/docs)
- Dataset schema: `hvac_construction_dataset/README.md`

---

*Dataset generated for educational purposes. No real project data included.*
