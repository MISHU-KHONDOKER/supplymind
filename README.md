# SupplyMind

> Autonomous multi-agent AI platform for supply chain intelligence — monitors suppliers, detects demand anomalies, generates procurement recommendations, and produces executive briefings. Production-grade. Fully containerised. Continuously evaluated.

---

## The Business Problem

Modern supply chains generate enormous operational signal — order volumes, supplier delivery times, return rates, demand fluctuations, market prices — across thousands of products and hundreds of suppliers. The data exists. The intelligence layer is missing.

Today, this work is done manually:

- **Procurement analysts** spend 60% of their time pulling reports from disconnected systems instead of making decisions.
- **Operations teams** discover supplier disruptions days after they happen, when the impact has already hit revenue.
- **Demand anomalies** — sudden spikes, unusual drops, fraud patterns — are caught reactively, not predicted.
- **Executive briefings** are assembled by hand every Monday morning by someone who'd rather be doing strategic work.

The result: companies lose millions to preventable disruptions, slow procurement cycles, and decisions made on stale information.

SupplyMind is the intelligence layer. Six specialised AI agents monitor, analyse, recommend, validate, and report — autonomously, continuously, and observably. The team gets back the time, and decisions get back the accuracy.

---

## Architecture

SupplyMind is built in five distinct layers, each with a single clear responsibility.

```

┌─────────────────────────────────────────────────────────────────┐
│  Frontend Layer        │  React dashboard · Live agent feed     │
├─────────────────────────────────────────────────────────────────┤
│  API Gateway Layer     │  FastAPI · Auth · WebSocket streaming  │
├─────────────────────────────────────────────────────────────────┤
│  Agent Orchestration   │  LangGraph state machine (6 agents)    │
├─────────────────────────────────────────────────────────────────┤
│  Tool & Data Layer     │  Web search · RAG · Anomaly engine     │
├─────────────────────────────────────────────────────────────────┤
│  Production Infra      │  Docker · K8s · Prometheus · Grafana   │
└─────────────────────────────────────────────────────────────────┘

```

### The Six Agents

```

| Agent | Responsibility | Output |
|---|---|---|
| **Planner** | Decomposes incoming tasks into agent-specific sub-tasks | Execution plan |
| **Monitor** | Watches supplier KPIs and order metrics continuously | Real-time alerts |
| **Analyst** | Detects anomalies using statistical + GAN-augmented methods | Anomaly report with confidence scores |
| **Recommender** | Generates procurement actions based on analysis | Ranked action recommendations |
| **Critic** | Validates every agent output for hallucinations and quality | Pass/fail with reasoning |
| **Reporter** | Synthesises results into executive briefings | Markdown briefing document |

```

Agents communicate through a shared `TypedDict` state managed by LangGraph. The pipeline supports conditional branching, parallel execution, and short-circuit on empty output.

### Key Design Decisions

- **LangGraph over CrewAI** — explicit state machine with conditional edges gives precise control over agent flow and failure recovery, which CrewAI's role-based abstraction does not expose.
- **TypedDict over Pydantic for shared state** — minimal runtime overhead, static type checking, and zero serialisation cost between agents. Pydantic is used only at the API boundary.
- **Critic agent as first-class citizen** — every other agent's output passes through validation before reaching the user. This makes the system trustworthy enough for production, not just functional in demos.
- **Hugging Face local inference** — no external API dependencies, no data egress, no rate limits. Aligns with regulated industries where data cannot leave premises.

---

## Engineering Highlights

This project deliberately demonstrates production-grade patterns that distinguish AI engineering from AI experimentation.

### Reliability

- **Two-layer hallucination defence in the Critic agent.** Outputs pass both a prompt-level structural validator (does the response match the required schema?) and a post-generation factual validator (does every claim reference data in the shared state?). Mirrors techniques from my published research on protocol-aware generation in cybersecurity AI.
- **Circuit breaker pattern on all external tool calls.** After N consecutive failures, the breaker opens and fails fast for a cooldown window instead of cascading timeouts through the pipeline.
- **Exponential backoff with Tenacity on all LLM inference calls.** Handles transient model server failures without surfacing them to the user.
- **Conditional short-circuit edges in LangGraph.** If any stage produces no output, the pipeline routes to END instead of running downstream agents on empty input.

### Observability

- **Custom Prometheus metrics on every agent invocation.** Tracks calls per minute, p50/p95/p99 latency, error rate, and cost per run — broken down by agent.
- **Pre-built Grafana dashboards** with SLO panels: hallucination rate, task completion rate, end-to-end pipeline latency, and per-agent failure rate.
- **Structured JSON logging with correlation IDs.** Every request gets an ID that propagates through every agent call, making distributed debugging trivial.
- **WebSocket streaming of agent thoughts** to the frontend, so users see what each agent is doing in real time — not just the final answer.

### Evaluation

- **Automated evaluation framework runs on every CI/CD build.** Golden test set covers happy paths, edge cases, adversarial inputs, and known regression scenarios.
- **Per-agent quality metrics** — not just system-level. The Critic agent's own decisions are evaluated by a separate eval set to prevent silent quality drift.
- **Hallucination rate, task completion rate, latency, and cost** are tracked over time, surfacing regressions before they reach production.

### Domain Intelligence

- **Anomaly detection module powered by techniques from published GAN-based intrusion detection research.** Applied here to supply chain time-series data — protocol-aware generation methodology transfers cleanly across domains.
- **Hybrid retrieval in the RAG layer** — dense semantic search via ChromaDB plus keyword fallback for entity-specific queries (product IDs, supplier names, SKUs).
- **Strategy pattern in the Recommender agent.** Picks between proactive recommendation (when anomaly confidence is high) and conservative monitoring mode (when data is ambiguous) — preventing overconfident actions on weak signals.

---

## Technology Stack

```

| Layer | Technology | Why |
|---|---|---|
| **Orchestration** | LangGraph | Explicit state machine with conditional edges and short-circuit support |
| **LLM Inference** | Hugging Face Transformers + local models | No API dependency, no data egress, runs on consumer hardware |
| **LLM Interface** | LangChain | Model-swappable abstraction over any OpenAI-compatible endpoint |
| **Retrieval** | ChromaDB + Sentence-Transformers | Local vector store, no managed service required |
| **Backend** | FastAPI + Uvicorn | Async-first, OpenAPI auto-generated, production-tested |
| **Frontend** | React + Vite + TailwindCSS | Standard professional stack with fast dev loop |
| **Validation** | Pydantic (API boundary) + TypedDict (internal state) | Strict validation where untrusted, zero-overhead where trusted |
| **Resilience** | Tenacity (retry) + custom circuit breaker | Standard reliability patterns from distributed systems |
| **Observability** | Prometheus + Grafana | Industry standard, OpenTelemetry-compatible |
| **Containerisation** | Docker + Docker Compose | Reproducible local environment for every service |
| **Orchestration (Infra)** | Kubernetes via Minikube | Production-style deployment locally for development |
| **CI/CD** | GitHub Actions | Lint, test, eval, build, deploy on every commit |
| **Configuration** | python-dotenv + Pydantic Settings | Type-safe environment configuration |
| **Logging** | structlog | Structured JSON logging with correlation IDs |
| **Testing** | pytest + pytest-asyncio | Industry standard, async-capable |

```

---

## Project Structure

```
supplymind/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI entry point
│   │   ├── api/
│   │   │   └── v1/
│   │   │       ├── routes.py        # REST endpoints
│   │   │       └── websocket.py     # Live agent streaming
│   │   ├── agents/
│   │   │   ├── planner.py
│   │   │   ├── monitor.py
│   │   │   ├── analyst.py
│   │   │   ├── recommender.py
│   │   │   ├── critic.py
│   │   │   └── reporter.py
│   │   ├── graph/
│   │   │   ├── state.py             # Shared TypedDict state
│   │   │   └── pipeline.py          # LangGraph graph definition
│   │   ├── tools/
│   │   │   ├── web_search.py
│   │   │   ├── vector_store.py
│   │   │   ├── anomaly_engine.py
│   │   │   └── llm_router.py
│   │   ├── evaluation/
│   │   │   ├── evaluator.py         # Scores every agent output
│   │   │   └── metrics.py           # Prometheus metric definitions
│   │   ├── core/
│   │   │   ├── config.py            # Settings via Pydantic
│   │   │   └── logging.py           # structlog setup
│   │   └── data/
│   │       └── synthetic/           # Demo supply chain dataset
│   ├── tests/
│   │   ├── test_agents.py
│   │   ├── test_pipeline.py
│   │   └── test_api.py
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Dashboard.jsx
│   │   │   ├── AgentFeed.jsx
│   │   │   └── Analytics.jsx
│   │   ├── api/
│   │   │   └── client.js
│   │   └── App.jsx
│   ├── Dockerfile
│   └── package.json
├── infra/
│   ├── docker-compose.yml           # Local full-stack
│   ├── prometheus.yml               # Scrape config
│   └── grafana/
│       └── dashboards/
│           └── supplymind.json
├── .github/
│   └── workflows/
│       ├── ci.yml                   # Lint, test, eval
│       └── deploy.yml               # Build and publish images
├── docs/
│   ├── architecture.md
│   └── agent-contracts.md
├── .env.example
├── Makefile                         # make run, test, build, deploy
└── README.md

```

### Why This Structure

- **`backend/` and `frontend/` are siblings, not nested.** This makes them independently deployable. The frontend has its own Dockerfile and can be served from a CDN, while the backend scales separately.
- **`agents/`, `tools/`, `graph/` are distinct.** Agents *decide* what to do. Tools *do* the work. The graph *wires them together*. Mixing these is the most common architectural mistake in agentic systems.
- **`evaluation/` is a first-class module, not an afterthought.** It contains both Prometheus metric definitions and the eval harness. Evaluation infrastructure should live alongside the system it evaluates — not in a notebook somewhere.
- **`core/` holds cross-cutting concerns.** Configuration and logging are needed everywhere; putting them in `core/` prevents circular imports.
- **`infra/` is separate from application code.** Operational concerns (Docker Compose, Prometheus config, Grafana dashboards) belong outside the application package. This separation makes it easy to swap infrastructure without touching code.
- **`docs/` for design documents, not generated docs.** Architecture decisions, agent contracts, and design notes live here. API docs are auto-generated from FastAPI and don't belong in the repo.
- **`Makefile` for common commands.** New contributors run `make run` instead of memorising six docker-compose flags. Self-documenting commands.

---

## Getting Started

### Prerequisites

- Python 3.10 or higher
- Node.js 18 or higher
- Docker Desktop running
- Git
- 8GB RAM minimum (16GB recommended for full stack)

### Quick Start

```bash
# Clone the repository
git clone https://github.com/<your-username>/supplymind.git
cd supplymind

# Copy environment template
cp .env.example .env

# Start the full stack
make run
```

That's it. The system will be available at:

- **Frontend dashboard** — http://localhost:3000
- **Backend API** — http://localhost:8000
- **API docs (auto-generated)** — http://localhost:8000/docs
- **Prometheus** — http://localhost:9090
- **Grafana** — http://localhost:3001 (login: admin / admin)

### Verify the Installation

Once the stack is running, verify each service:

```bash
make health
```

This runs a smoke test against every component and reports status. All checks should pass before you run anything else.

### Manual Setup (Without Docker)

If you want to develop without Docker, see [docs/local-development.md](docs/local-development.md).

### Common Commands

```bash
make run        # Start the full stack (Docker Compose)
make stop       # Stop all services
make test       # Run the test suite
make eval       # Run the evaluation harness
make logs       # Tail logs from all services
make clean      # Remove containers, volumes, and build artifacts
make deploy     # Build and push production images
```

### Configuration

All configuration lives in `.env` (created from `.env.example`). Key settings:

```

| Variable | Purpose | Default |
|---|---|---|
| `LLM_MODEL` | Hugging Face model identifier | `Qwen/Qwen2.5-1.5B-Instruct` |
| `EMBEDDING_MODEL` | Sentence-Transformers model | `all-MiniLM-L6-v2` |
| `PROMETHEUS_PORT` | Metrics server port | `9090` |
| `LOG_LEVEL` | Logging verbosity | `INFO` |
| `EVAL_ON_STARTUP` | Run eval suite when API starts | `false` |

```

See `.env.example` for the complete list.

### Troubleshooting

**Docker Desktop won't start** — Ensure WSL 2 is installed (`wsl --install`) and virtualization is enabled in BIOS.

**Port already in use** — Another service is using a required port. Run `make stop` then `make run` again, or override ports in `.env`.

**Out of memory** — Reduce the LLM model size by setting `LLM_MODEL=Qwen/Qwen2.5-0.5B-Instruct` in `.env`. The 0.5B model runs comfortably on 4GB RAM.

**Slow first run** — First startup pulls Docker images and downloads the LLM (~3GB). Subsequent starts are fast.

---

## Performance and Metrics

The system is benchmarked on a representative supply chain dataset. All measurements are captured automatically by the Prometheus integration and reproducible via `make benchmark`.

```
### Throughput and Latency

| Metric | p50 | p95 | p99 |
|---|---|---|---|
| End-to-end pipeline latency | _TBD_ | _TBD_ | _TBD_ |
| Planner agent | _TBD_ | _TBD_ | _TBD_ |
| Monitor agent | _TBD_ | _TBD_ | _TBD_ |
| Analyst agent | _TBD_ | _TBD_ | _TBD_ |
| Recommender agent | _TBD_ | _TBD_ | _TBD_ |
| Critic agent | _TBD_ | _TBD_ | _TBD_ |
| Reporter agent | _TBD_ | _TBD_ | _TBD_ |

### Quality Metrics

| Metric | Value | Method |
|---|---|---|
| Hallucination rate | _TBD_ | Critic agent validation against shared state |
| Task completion rate | _TBD_ | Percentage of pipelines reaching Reporter successfully |
| Anomaly detection precision | _TBD_ | Against labelled synthetic test set |
| Anomaly detection recall | _TBD_ | Against labelled synthetic test set |

### Resource Usage

| Resource | Idle | Under Load |
|---|---|---|
| CPU (single inference run) | _TBD_ | _TBD_ |
| Memory (full stack) | _TBD_ | _TBD_ |
| Disk (LLM weights + vector store) | _TBD_ | _TBD_ |

```

### Cost per Run

Running fully locally on CPU, the marginal cost per pipeline run is **zero** — no API calls, no managed services. Compute cost is amortised across the local hardware.

For comparison, an equivalent pipeline calling GPT-4 via OpenAI API would cost approximately _TBD_ per run at current pricing.

### Reproducing the Benchmarks

```bash
make benchmark
```

This runs the full benchmark suite — 100 pipeline executions across synthetic scenarios spanning normal operations, anomaly events, and adversarial inputs. Results are written to `benchmarks/results_<timestamp>.json`.

---

## Known Limitations

Being honest about what is and is not in the current version:

### Model Quality

- **Inference quality scales with model size.** The default `Qwen2.5-1.5B-Instruct` is fast and resource-efficient, but generation quality is below frontier cloud models. Swap to `Qwen2.5-7B-Instruct` or any OpenAI-compatible cloud endpoint with a single config change.
- **No fine-tuning yet.** All agents use prompt engineering on base models. A domain-tuned model via QLoRA on supply chain documents would meaningfully improve the Recommender and Reporter agents.

### Memory and Context

- **No long-term memory across pipeline runs.** Each invocation is stateless. The system cannot say "we already flagged this supplier last week, do not flag again." A future version could add a memory layer using episodic storage in ChromaDB.
- **Context window is bounded by the underlying model.** For long supply chain incident histories, retrieval is selective rather than exhaustive. Hierarchical summarisation is a planned addition.

### Scope and Domain

- **Synthetic dataset only.** The system ships with a realistic but synthetic supply chain dataset for reproducibility. Real production deployment would require integration with the company's ERP, procurement, and supplier management systems.
- **English-only briefings.** Reporter outputs are in English. Multilingual support (Mandarin, Spanish, German) is straightforward with prompt-level instructions but not validated.

### Operational

- **No multi-tenancy.** The system is single-tenant by design — one organisation's data per deployment. Multi-tenant isolation with proper row-level security is a significant additional design effort.
- **No human-in-the-loop approval flow.** The Recommender produces recommendations directly to the Reporter. A production deployment would benefit from a review queue where critical recommendations are approved before being included in executive briefings.
- **Kubernetes deployment validated on Minikube only.** Production deployment on managed Kubernetes (EKS, GKE, AKS, Alibaba ACK) requires standard cloud-specific configuration that is documented but not bundled.

### Evaluation

- **Golden test set is bootstrapped, not exhaustive.** Coverage of edge cases and adversarial inputs is intentional but limited. Real production evaluation requires continuous expansion of the test set based on production failures — which by definition does not exist yet for this project.

---

## Roadmap

Planned improvements, in rough priority order:

- [ ] **v0.2 — Domain-tuned LLM.** Fine-tune `Qwen2.5-1.5B` on supply chain documents via QLoRA. Drop in as a new model option in the LLM router.
- [ ] **v0.3 — Long-term memory layer.** Episodic memory store in ChromaDB with summarisation and age-out policy.
- [ ] **v0.4 — Human-in-the-loop approval.** Review queue for high-impact recommendations before they reach executive briefings.
- [ ] **v0.5 — Multilingual reporter.** Executive briefings in English, Mandarin, Spanish, German via prompt-level localisation.
- [ ] **v0.6 — Production cloud deployment.** Validated deployment manifests for Alibaba Cloud ACK, AWS EKS, and GCP GKE.
- [ ] **v1.0 — Multi-tenancy.** Row-level isolation, tenant-aware logging, namespace-scoped vector stores.

---

## Acknowledgements

This project draws on patterns and techniques from:

- **LangGraph** for explicit state machine semantics in agentic systems.
- **My published research** on protocol-aware GAN frameworks for class-imbalanced anomaly detection, originally applied to network intrusion data (IEEE ICCBDAI 2025, Best Oral Presentation Award), adapted here for supply chain anomalies.
- **Industry production patterns** for circuit breakers, exponential backoff, and observability — standard in distributed systems literature.
- **The open-source ecosystem** — Hugging Face, ChromaDB, FastAPI, Prometheus, Grafana, and the broader Python data stack.

---

## About

Built by **Mohyminul Islam** as an applied AI engineering portfolio project demonstrating production-grade agentic systems with full observability, evaluation, and CI/CD.

- 🎓 M.S. Software Engineering — Northwestern Polytechnical University, Xi'an (985 / Double First-Class)
- 🏆 IEEE ICCBDAI 2025 — Best Oral Presentation Award (Generative AI for Cybersecurity)
- 📄 Two journal submissions under review (Wiley SCI, Springer Nature)
- 🔗 [LinkedIn](https://www.linkedin.com/in/mohyminul-islam-mishu-9977bb115/) · [GitHub](https://github.com/MISHU-KHONDOKER)

---

## License

MIT — see [LICENSE](LICENSE).

---

*This is a portfolio project. The synthetic dataset and scenarios are designed to mirror real supply chain operations but do not reflect any specific company's data.*