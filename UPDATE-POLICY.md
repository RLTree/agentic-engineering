# Research and Compatibility Update Policy

## Research lock

This release is current through **2026-07-22, America/Los_Angeles**.

## Re-verify before changing or hard-coding

- GPT-5.6 Sol model name, availability, effort/power settings, Max/Ultra behavior and Codex CLI syntax;
- Codex plugin manifest/marketplace schema, installation UI/commands, skill metadata limits and optional `agents/openai.yaml` fields;
- AGENTS.md precedence/size behavior;
- MCP and A2A protocol versions, SDK maturity and transport/capability support;
- Rust/Tokio/Cargo/Miri/Loom/RustSec APIs and recommended commands;
- agent-framework and durable-runtime semantics.

Use official/primary sources first. Record access date and change the research lock when findings alter behavior.

## Update triggers

- Codex changelog changes plugin, skill, subagent, permission or model behavior;
- a source marked official becomes deprecated or superseded;
- routing/eval production failure repeats;
- new security incident affects tools, protocols, plugins, memory or effects;
- Rust fragments no longer compile under the supported toolchain;
- blind Sol A/B fails to show benefit or reveals a regression;
- user corrections show that a concept is missing or over-prescribed.

## Change protocol

1. capture the change and affected source IDs;
2. update `SOURCE-MANIFEST.json`, `EVIDENCE-MATRIX.csv` and `RESEARCH.md` together;
3. write the expected decision delta;
4. update only the skills/references/assets/scripts implicated;
5. add positive, negative and ambiguous eval cases;
6. run all mandatory release gates and target-environment checks where available;
7. update version, changelog, file manifest and confidence;
8. preserve or explicitly migrate compatibility for existing skill names and links.

## Deprecation

Mark superseded guidance before removal. Prefer compatibility notes and a migration path when renaming skills, schemas or templates. Never silently reinterpret an effect, approval or replay contract for in-flight durable systems.
