# TRION Documentation: Concepts & User Guide

Welcome to TRION's user-facing documentation. These guides are written for end-users, system administrators, and integrators who want to understand the concepts, security features, and benefits of TRION. 

Unlike developers who need to read the source code, this documentation explains **how TRION works conceptually** to make AI agent execution safe, reliable, and predictable. No programming experience is required.

---

## Guide Index

Explore our core cognitive concepts:

### 🎹 [1. PIANO Architecture Concept](file:///Users/denniskassner/Documents/trion-docs/docs/website/piano_concept.md)
* **What it is:** The structural foundation of TRION.
* **Why it matters:** It explains how TRION separates logic from behavior using a central decision gateway (the bottleneck) and dynamic rules tables, preventing the agent from acting uncontrollably.

### 🧠 [2. TMR Concept (Consistent Intent)](file:///Users/denniskassner/Documents/trion-docs/docs/website/tmr_concept.md)
* **What it is:** TRION's semantic translation layer (TRION Meaning Representation).
* **Why it matters:** It shows how TRION abstracts away language (German, English, mixed phrasing) and paraphrasing. This ensures that the agent understands the exact meaning of your request consistently.

### 📑 [3. Operation Contract Concept (Ironclad Security)](file:///Users/denniskassner/Documents/trion-docs/docs/website/operation_contract_concept.md)
* **What it is:** The mathematical boundary gatekeeper for tool execution.
* **Why it matters:** It explains how TRION restricts the agent to a pre-authorized contract. This blocks unauthorized actions (such as destructive system commands or prompt injection tricks) and halts endless loops automatically.

---

## Core Philosophy

TRION is built on **Zero Trust Agent Execution**. 

Most AI assistants are given tools and trusted to use them correctly. TRION is different. By separating **meaning** from **action**, TRION forces the AI to sign a static contract of what it is allowed to do before it is allowed to touch any system resource or execute any tool. 
