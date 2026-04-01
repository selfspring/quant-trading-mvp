---
name: dual-track-memory
description: Use this skill to hierarchically store or semantically recall project memories (L0 abstract, L1 rules, L2 raw logs) via SQLite and ChromaDB. Overrides default memory.
---

# Dual-Track Memory Skill (双轨记忆引擎)

This skill overrides the default memory system, providing an enterprise-grade L0/L1/L2 memory architecture powered by SQLite + ChromaDB. It ensures transactions, zero data-loss during concurrency, and robust semantic retrieval.

## Tools

### store_memory
**Description**: Store a new memory hierarchically into the Dual-Track system. It saves L0 (for vector search), L1 (for context injection), and L2 (full raw markdown file), resolving the database locks automatically.

**Parameters** (Pass via temporary JSON file, NEVER via stdin string):
Create a file named `tmp_memory.json` in your workspace containing:
```json
{
  "scope": "project/quant-trading",
  "l0_summary": "1-sentence abstract. This is the ONLY thing embedded into the vector DB for semantic search. Keep it dense and searchable.",
  "l1_summary": "The core points or rules (around 500 chars). This is what gets injected into the Agent's context when recalled.",
  "l2_content": "The FULL raw content (stack traces, long code blocks, full chat logs). Written to disk as a markdown file."
}
```

**Command**:
```bash
python scripts/memory_tool.py store --file tmp_memory.json
```

### recall_memory
**Description**: Semantically search the memory base using ChromaDB and return the structured L1 context along with Graph edges from SQLite.

**Parameters**:
- `query` (string, required): Natural language search query.
- `n_results` (number, optional): Number of top results to return. Default is 3.

**Command**:
```bash
python scripts/memory_tool.py recall --query "Your search query" --n_results 3
```
