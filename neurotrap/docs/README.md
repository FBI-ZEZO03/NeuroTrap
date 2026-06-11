# NeuroTrap CADN — Documentation Index

| # | Document | What it covers |
|---|----------|---------------|
| — | [architecture.md](architecture.md) | System layer diagram, component responsibilities, data flow |
| 01 | [01_system_overview.md](01_system_overview.md) | Full 10-layer architecture, Docker topology, component map, data flow narrative |
| 02 | [02_installation.md](02_installation.md) | Production deployment, host hardening, Docker setup, SSL, first-run checklist |
| 03 | [03_honeypots.md](03_honeypots.md) | Cowrie, OpenCanary, Galah, native sensors — config, log format, network isolation |
| 04 | [04_detection.md](04_detection.md) | AlertEvent schema, PacketMonitor, LogIngestionPipeline, CowrieSessionBuilder |
| 05 | [05_behavior_analysis.md](05_behavior_analysis.md) | Feature engineering, ML classifier, TTP extraction, threat score formula |
| 06 | [06_deception_engine.md](06_deception_engine.md) | Environment templates, DeceptionEngine, CredentialGenerator, lifecycle management |
| 07 | [07_cbee.md](07_cbee.md) | Cognitive Bias Exploitation Engine — 5 dimensions, scoring, bait injection |
| 08 | [08_gadcf.md](08_gadcf.md) | Generative fake content factory — asset types, LLM + template mode |
| 09 | [09_digital_twin.md](09_digital_twin.md) | Attacker Digital Twin, Markov predictor, kill-chain mapper |
| 10 | [10_fhim.md](10_fhim.md) | Federated Honeypot Intelligence Mesh — FedAvg, differential privacy |
| 11 | [11_soc_analyst.md](11_soc_analyst.md) | AI SOC Analyst — triage, incident reports, Q&A, shift summary |
| 12 | [12_response_engine.md](12_response_engine.md) | Decision matrix, iptables/tc enforcement, alert channels |
| 13 | [13_dashboard.md](13_dashboard.md) | SPA sections, live feed, WebSocket events, frontend structure |
| 14 | [14_security.md](14_security.md) | Network isolation, host hardening, JWT/MFA, container security |
| 15 | [15_testing.md](15_testing.md) | pytest suite, test patterns, CI pipeline, attack simulation |
| 16 | [16_developer_guide.md](16_developer_guide.md) | Local dev setup, DB layer, API conventions, common commands |
| — | [api-reference.md](api-reference.md) | Full REST API reference with request/response examples |

---

## Database Documentation

Schema, models, indexing, and deployment docs for the MongoDB layer live in `../../neurotrap-db/docs/`:

| File | What it covers |
|------|---------------|
| `01_architecture_overview.md` | DB conventions, ID strategy, naming rules |
| `02_collection_list.md` | All 28 collections with write rate and retention tier |
| `03_relationship_diagram.md` | Mermaid ER diagram |
| `04_data_flow_diagram.md` | Ingest → enrich → respond → report flow |
| `05_indexing_strategy.md` | Per-collection indexes with rationale |
| `06_security_best_practices.md` | RBAC, encryption, field-level protection |
| `07_scalability.md` | Sharding keys, capped collections, tiering |
| `08_retention_strategy.md` | TTL indexes, archival rules |
| `09_backup_strategy.md` | Snapshot cadence, PITR, restore drills |
| `10_elasticsearch_integration.md` | ES mappings, sync mechanism |
| `11_production_deployment.md` | Topology, sizing, monitoring |
| `12_final_architecture_diagram.md` | Enterprise architecture Mermaid diagram |
