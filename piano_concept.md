# PIANO Architecture: The Cognitive Engine of TRION

TRION is built on a clean, modular layer system designed to make AI agent behavior predictable, safe, and easily configurable. At the heart of TRION's design is the **PIANO** architectural pattern.

PIANO stands for **Parallel Iterative ANalogical Organization**, a cognitive architecture model from cognitive science. In TRION, we adapt this model to create a highly robust, rule-driven orchestrator that ensures safety and flexibility.

---

## Core Concept: Why PIANO?

In typical AI systems, the rules governing how the agent responds, which tools it selects, and how safety is handled are often scattered throughout the codebase. This leads to:
* **Brittle code:** Changes in behavior require modifying the application source code.
* **Unpredictability:** It is hard to guarantee that the AI will follow specific safety protocols in every situation.
* **Lack of transparency:** There is no single source of truth for the agent's behavior rules.

TRION solves this by implementing the core principles of the PIANO model.

```
                  +-----------------------------------+
                  |      Shared Behavior Layer        |
                  |  (Rules, Safety Policies, Maps)   |
                  +-----------------+-----------------+
                                    |
                                    v
+------------+    +-----------------+-----------------+    +-------------+
| User Input |--->|    Unified Bottleneck (Filter)    |--->| Next Stage  |
+------------+    +-----------------------------------+    +-------------+
```

---

## The Three Pillars of PIANO in TRION

### 1. The Central Bottleneck (`routing_frame`)
Before the system makes any complex decisions or executes LLM (Large Language Model) reasoning steps, the input passes through a single, central gateway called the **Bottleneck**. 

* **How it works:** All classification, intent detection, and safety signals are collected and combined into a single structured frame (the `routing_frame`).
* **Why it matters:** Downstream modules do not make independent, ad-hoc decisions based on the raw input. They must read from this central bottleneck. This ensures that safety filters and execution choices are applied consistently across the entire pipeline.

### 2. The Shared Behavior Layer (`intelligence_modules`)
No core component of TRION is allowed to carry its own behavioral rules. All configurations, prompt templates, tool mappings, and safety rules are stored in a dedicated, externalized layer.

* **Logik vs. Behavior:** The Python code defines *how* to execute tasks (the logic), while the configuration files (like CSVs and templates) define *what* behavior is allowed.
* **Easy Customization:** Users and administrators can modify TRION's behavior, add safety keywords, or adjust routing rules simply by updating configuration files, without needing to write code or rebuild the application.

### 3. Modularity and Extensibility
By decoupling the rules from the engine, TRION remains lightweight and highly maintainable.
* **Independent Tooling:** Adding new tools or Model Context Protocol (MCP) integrations doesn't require modifying the core runner. The new tools simply register their capabilities in the shared behavior layer, and TRION automatically learns how to routing-classify them.

---

## Benefits for Integrators and Users

> [!TIP]
> **Deterministic Safety**
> By utilizing a central bottleneck and structured configuration files, TRION guarantees that safety filters and domain blocks cannot be bypassed by LLM hallucinations.

* **No Code Drift:** System behavior is predictable because the rules are clearly defined in a single place.
* **No Big-Bang Rewrites:** Adding features is a surgical process of extending configuration tables rather than refactoring monolithic files.
* **Transparent Governance:** Administrators can audit exactly what rules the agent is following by looking at the shared behavioral CSV files.



<p align="center">
<img width="1307" height="3612" alt="PIANO Architecture - Standalone" src="https://github.com/user-attachments/assets/d536bef1-2999-4595-ace5-1d9c051f3ffd" />
</p>
