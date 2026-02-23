# Architectural Analysis: Ghostclaw (ghostclaw-refactored)

## 1. Evaluation of Layering

The current architecture in the `ghostclaw-refactored` branch shows a clear attempt at modularization, but several "leaky abstractions" and layering violations persist.

### 1.1 Current Layers
- **CLI Layer (`cli/`)**: Handles user interaction. Generally well-separated.
- **Orchestration Layer (`core/analyzer.py`)**: Responsible for the analysis pipeline. Currently "fat"—it handles I/O, base metrics, and orchestration.
- **Stack Layer (`stacks/`)**: Technology-specific logic. Good use of the Strategy pattern via `StackAnalyzer`.
- **Infrastructure Layer (`lib/`)**: Utility modules for external integrations.

### 1.2 Leaky Abstractions
- **I/O Leakage**: `CodebaseAnalyzer` directly reads files and counts lines. This makes it tied to the filesystem and limits its ability to work with other data sources (e.g., in-memory files for testing or cloud storage).
- **Metric Confusion**: The responsibility for defining "what is a large file" is split between `CodebaseAnalyzer` (defaults), `StackAnalyzer` (thresholds), and `RuleValidator` (YAML rules).
- **Coupling Engine Duplication**: `NodeImportAnalyzer` and `PythonImportAnalyzer` both implement their own graph traversal and cycle detection logic, leading to divergent implementations of the same mathematical concepts.

---

## 2. Critical Weaknesses

### 2.1 The "God Orchestrator" (`CodebaseAnalyzer`)
`CodebaseAnalyzer` violates the Single Responsibility Principle. It:
1. Performs Tech Stack Detection.
2. Manages File Discovery.
3. Calculates Base Metrics (Line Counts).
4. Orchestrates Stack-Specific Analysis.
5. Invokes Rule Validation.
6. Computes the final Vibe Score.

### 2.2 Lack of Dependency Injection
Dependencies like `RuleValidator` and the various `StackAnalyzer` implementations are instantiated internally or retrieved via a global registry. This makes the system rigid and difficult to unit test without complex mocking.

### 2.3 Fragile Rule Engine
`RuleValidator` is disconnected from the data acquisition phase. It receives a `report` but lacks access to the raw file list or the import graph, making it impossible to enforce rules like "Layer Violations" or "Naming Conventions" effectively.

### 2.4 Maintenance Overhead
Adding a new language requires:
1. Creating a new `StackAnalyzer`.
2. Implementing a language-specific coupling analyzer (often duplicating graph logic).
3. Updating the `STACK_REGISTRY`.
4. Potentially updating `CodebaseAnalyzer` if new base metrics are needed.

---

## 3. Proposed Optimization Strategy

### 3.1 Architectural Patterns to Adopt
- **Repository Pattern**: Abstract all filesystem access behind a `SourceRepository` interface.
- **Dependency Injection (DI)**: Use a Container or simple Constructor Injection to provide `RuleValidator`, `MetricsCollector`, and `StackAnalyzers` to the orchestrator.
- **Service Layer**: Extract the Vibe Score calculation and Metric collection into dedicated services.
- **Template Method / Base Class**: Extract common graph logic (cycle detection, instability calculation) into a `BaseImportAnalyzer`.

### 3.2 Structured Roadmap

#### Phase 1: Infrastructure Refinement (Immediate)
- Extract common graph logic from `core/coupling.py` and `core/node_coupling.py`.
- Implement `Repository` pattern for file access.

#### Phase 2: Orchestration Decoupling (Short-term)
- Refactor `CodebaseAnalyzer` to accept injected dependencies.
- Introduce an `AnalysisContext` object to carry state through the pipeline.
- Create a `MetricsService` to handle line counts and file sizes.

#### Phase 3: Plugin System & Rule Enhancement (Mid-term)
- Implement the Plugin System proposed in `phase7.md`.
- Enhance `RuleValidator` to accept a "Context" object containing the File List, Import Graph, and Metrics.

#### Phase 4: Scalability (Long-term)
- Introduce parallel file processing for large repositories.
- Add support for cross-language analysis (e.g., Node.js frontend calling a Python backend).
