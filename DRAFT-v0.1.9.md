# Draft: v0.1.9 — next milestone

This document outlines the plan for the v0.1.9 release cycle, building on the v0.1.8 modular CLI foundation and targeting polish, hardening, and MCP/ecosystem improvements.

1) Goals
- Finish polish and stabilization of the modular CLI
- Harden core services and tests, raise test coverage
- Improve performance and observability for large repos
- Stabilize MCP integration and plugin ecosystem
- Prepare upgrade path and developer docs

2) Scope (content areas)
- Core CLI and architecture
  - Complete consolidation of formatter/utility exports and public API
  - Remove remaining legacy code paths not production-safe
  - Ensure consistent error messaging and exit codes
- Performance and scaling
  - Fine-tune auto-parallel heuristics (thresholds, fallbacks)
  - Add per-command timing gates and dashboards for quick diagnosis
  - Improve caching granularity and eviction strategy
- Testing and quality
  - Expand unit/integration tests toward 90–95% coverage
  - Add end-to-end tests for major flows (analyze, MCP calls, plugin flows)
  - Strengthen mocking patches to decouple tests from internal wiring
- MCP and ecosystem
  - Harden MCP server interactions (batch calls, streaming results)
  - Document MCP usage patterns and add a sample workflow
  - Validate bridge/server commands against IDE scenarios
- Documentation and onboarding
  - Update CHANGELOG with v0.1.9 goals and plan
  - Add Performance & Troubleshooting section
  - Publish a migration guide for deprecated internal APIs
- Developer experience
  - Improve repo bootstrap and developer guides
  - Add a small official sample repo for quick testing

3) Milestones (approx. timeline)
- Week 1: finalize scope, implement core polish items (error handling, logging, clarity)
- Week 2: expand perf profiling hooks, Harden MCP flow, tests; begin migration docs
- Week 3: complete MCP/bridge polish, end-to-end tests, docs; update MEMORY/CHANGELOG
- Week 4: internal review, finalize PRs, plan for merge to main; release candidate prep

4) Deliverables
- v0.1.9 branch with completed polish, tests, and MCP improvements
- Updated CHANGELOG and MEMORY.md entries
- Profiling artifacts and profiles from large repos
- Documentation and migration notes

5) Risks and mitigations
- Risk: scope creep
- Mitigation: lock scope; track with changelog
- Risk: regression from removing legacy paths
- Mitigation: targeted tests; deprecation plan
- Risk: MCP integration instability
- Mitigation: explicit integration tests and repro workflow

6) Dependency and repo hygiene
- hermetic tests; avoid external services in unit tests
- keep branch manageable; small PRs
- maintain clear changelog entries

7) Next steps / ask
- Create v0.1.9 branch and start implementing plan
- Draft release notes outline for v0.1.9
- Prepare migration guide (internal API changes)
- Start with top-priority polish items (error handling, logging, CLI cleanup)

Would you like me to proceed with creating a v0.1.9 branch and begin implementation? If you have preferences for focus areas or cadence, share and I’ll tailor the plan.