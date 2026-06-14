from __future__ import annotations

from typing import Dict, Iterable, List


MASTER_SYSTEM_PROMPT = """You are an expert reverse-engineer, software architect, product analyst, and clean-room specification writer.

Your task is to analyze repository evidence and produce a self-contained clean-room rebuild blueprint that enables a separate coding agent to build a functionally similar software product from scratch without access to the original repository files.

You are not writing a code review, summary, or commentary. You are writing an implementation-ready rebuild specification.

Hard rules:
1. Do not copy source code, large code blocks, proprietary text, private assets, secrets, tokens, passwords, keys, or connection strings.
2. Do not instruct the downstream agent to copy code verbatim.
3. Use repository evidence only unless explicitly told otherwise.
4. Do not invent facts. Distinguish clearly between Evidence, Inference, Assumption, Gap, and Recommendation.
5. Every major claim must be grounded in repository evidence such as file paths, manifests, routes, schemas, tests, scripts, migrations, config files, or observed structural patterns.
6. If information is missing, provide the best evidence-based inference and label it clearly.
7. The final document must be self-contained. Do not rely on “see source file X” as a substitute for describing required behavior.
8. Prefer implementation contracts, behavior descriptions, schemas, tables, workflows, state transitions, diagrams, and concise original pseudocode where necessary.
9. Keep the document clean-room safe while still being detailed enough for an independent rebuild.
10. Be comprehensive, precise, and internally consistent. Avoid contradicting instructions or duplicate sections.

Output requirements:
- Return Markdown only.
- Write a complete rebuild blueprint, not notes to the analyst.
- Use clear section headings and structured tables where appropriate.
- Include Mermaid diagrams where architecture, workflows, or ER structure would improve implementation clarity.
- When a section is unsupported by evidence, say so explicitly and provide the strongest justified inference.
"""


SUMMARY_SYSTEM_PROMPT = """You are a technical code analyst helping build a clean-room rebuild blueprint.
Provide a concise but implementation-useful summary of a single file.
Do not write conversational filler.
Return only a raw JSON object with these keys:
{
  "responsibilities": ["2-5 concrete duties or behaviors"],
  "exports": ["important classes, functions, routes, handlers, jobs, or constants"],
  "dependencies": ["important imported packages, modules, or infrastructure dependencies"],
  "evidence": ["short bullet-style evidence statements tied to the file"]
}
"""


COMPONENT_SYSTEM_PROMPT = """You are an expert software architect producing clean-room component specifications.
Given grouped repository evidence, produce a detailed component synthesis that another engineer could use to rebuild the module without access to the original source.
Use implementation-ready language, cite evidence by file path, and clearly mark inferences when needed.
"""


ANALYSIS_STATE_SYSTEM_PROMPT = """You are an expert repository analyst building structured intermediate findings for a clean-room rebuild.
Return only valid JSON. Do not include markdown fences or explanatory text.
Prioritize evidence-based extraction. When uncertain, include the item under assumptions or gaps instead of presenting it as fact.
"""


ROLLING_STATE_SYSTEM_PROMPT = """You are an expert technical editor consolidating architectural findings between blueprint generation stages.
Summarize only durable implementation decisions, evidence-backed conclusions, unresolved gaps, and assumptions that later sections must honor.
Return concise markdown with bullet points and no conversational filler.
"""


SECTION_CHUNKS: List[Dict[str, object]] = [
    {
        "id": "foundation",
        "range_str": "Sections 0 to 6",
        "required_headings": [
            "## 0. Generation Metadata",
            "## 1. Clean-Room and License Boundary",
            "## 2. Executive Summary for the Rebuilding Agent",
            "## 3. Evidence Map",
            "## 4. Repository Inventory Summary",
            "## 5. Product Domain Model",
            "## 6. Technology Stack to Rebuild",
        ],
        "prompt": """Write these sections in markdown:
## 0. Generation Metadata
## 1. Clean-Room and License Boundary
## 2. Executive Summary for the Rebuilding Agent
## 3. Evidence Map
## 4. Repository Inventory Summary
## 5. Product Domain Model
## 6. Technology Stack to Rebuild

Requirements:
- Make the clean-room and license boundary explicit.
- Include evidence citations/tables wherever claims are made.
- Distinguish evidence, inference, assumptions, and gaps.
- Make Section 3 a strong evidence map, not filler prose.
""",
    },
    {
        "id": "functional_architecture",
        "range_str": "Sections 7 to 10",
        "required_headings": [
            "## 7. Full Functional Specification",
            "## 8. User Workflows and Behavior",
            "## 9. System Architecture Blueprint",
            "## 10. Low-Level Design for Rebuild",
        ],
        "prompt": """Write these sections in markdown:
## 7. Full Functional Specification
## 8. User Workflows and Behavior
## 9. System Architecture Blueprint
## 10. Low-Level Design for Rebuild

Requirements:
- Include a feature catalog plus detailed per-feature contracts.
- Include end-to-end workflows, validations, business rules, and edge cases.
- Include Mermaid diagrams for architecture and lifecycle/workflow views where useful.
- Describe modules/components/services in implementation-ready detail.
- Every major feature or component must cite evidence or explicitly state that it is an inference.
""",
    },
    {
        "id": "data_api_ui_security",
        "range_str": "Sections 11 to 14",
        "required_headings": [
            "## 11. Data Model Blueprint",
            "## 12. API and Integration Contracts",
            "## 13. UI/UX Rebuild Specification",
            "## 14. Security Blueprint",
        ],
        "prompt": """Write these sections in markdown:
## 11. Data Model Blueprint
## 12. API and Integration Contracts
## 13. UI/UX Rebuild Specification
## 14. Security Blueprint

Requirements:
- Include a Mermaid ER diagram in Section 11.
- For APIs, define endpoint catalogs and endpoint details with schemas, side effects, auth, and failure behavior.
- For UI/UX, provide screen/page catalogs and detailed screen contracts where a UI exists; state clearly if no UI exists.
- For security, cover auth, authorization, secret handling, validation, web/API security, file security, and minimum rebuild requirements.
""",
    },
    {
        "id": "ops_quality_delivery",
        "range_str": "Sections 15 to 19",
        "required_headings": [
            "## 15. Performance, Scalability, and Reliability Blueprint",
            "## 16. Build, Deployment, and Operations Blueprint",
            "## 17. Testing and Quality Blueprint",
            "## 18. Implementation Backlog for the Downstream Coding Agent",
            "## 19. Rebuild Readiness Checklist",
        ],
        "prompt": """Write these sections in markdown:
## 15. Performance, Scalability, and Reliability Blueprint
## 16. Build, Deployment, and Operations Blueprint
## 17. Testing and Quality Blueprint
## 18. Implementation Backlog for the Downstream Coding Agent
## 19. Rebuild Readiness Checklist

Requirements:
- Include operational, deployment, testing, and rebuild guidance that a downstream coding agent can execute without access to the original repo.
- Cover performance hot paths, scalability considerations, reliability boundaries, and observability.
- Provide a milestone-driven implementation backlog and a concrete readiness checklist.
- Preserve clean-room constraints throughout.
""",
    },
]


def build_file_summary_prompt(file_path: str, content: str) -> str:
    return (
        f"File relative path: {file_path}\n"
        "Source code or file contents follow. Summarize implementation-relevant behavior and dependencies.\n"
        "Source:\n"
        "```\n"
        f"{content[:20000]}\n"
        "```\n"
    )


def build_component_prompt(component_name: str, context_str: str) -> str:
    return (
        f"Component Name: {component_name}\n"
        "Files and evidence contained in this component:\n\n"
        f"{context_str}\n\n"
        "Produce a clean-room component synthesis with: responsibilities, public interfaces, dependencies, data ownership, "
        "failure behavior, security considerations, performance considerations, and evidence references."
    )


def build_analysis_state_prompt(
    repo_name: str,
    repo_url: str,
    file_tree: Iterable[str],
    manifests_content: str,
    component_specs: Dict[str, str],
) -> str:
    tree_str = "\n".join(list(file_tree)[:250])
    specs_excerpt = "\n\n".join(
        f"=== Component: {name} ===\n{spec}"
        for name, spec in list(component_specs.items())[:20]
    )
    return f"""Repository: {repo_name}
Repository URL: {repo_url}

Build a structured intermediate analysis state from the evidence below.

--- File Tree ---
{tree_str}

--- Manifest and Config Evidence ---
{manifests_content[:12000]}

--- Component Syntheses ---
{specs_excerpt[:20000]}

Return only valid JSON with this schema:
{{
  "product_summary": string,
  "actors": [{{"name": string, "purpose": string, "evidence": [string], "confidence": "high|medium|low"}}],
  "features": [{{"name": string, "summary": string, "evidence": [string], "confidence": "high|medium|low"}}],
  "entities": [{{"name": string, "summary": string, "evidence": [string], "confidence": "high|medium|low"}}],
  "api_contracts": [{{"name": string, "summary": string, "evidence": [string], "confidence": "high|medium|low"}}],
  "ui_surfaces": [{{"name": string, "summary": string, "evidence": [string], "confidence": "high|medium|low"}}],
  "security_findings": [{{"name": string, "summary": string, "evidence": [string], "confidence": "high|medium|low"}}],
  "operations_findings": [{{"name": string, "summary": string, "evidence": [string], "confidence": "high|medium|low"}}],
  "assumptions": [string],
  "gaps": [string]
}}
"""


def build_section_prompt(
    repo_name: str,
    repo_url: str,
    manifests_content: str,
    component_specs: Dict[str, str],
    analysis_state_markdown: str,
    rolling_state: str,
    chunk_prompt: str,
    file_tree: Iterable[str],
) -> str:
    tree_str = "\n".join(list(file_tree)[:220])
    specs_str = "\n\n".join(
        f"=== Component: {component_name} ===\n{spec}"
        for component_name, spec in component_specs.items()
    )
    return f"""Repository Name: {repo_name}
Repository URL: {repo_url}

You are given repository evidence collected from a software repository. Transform it into a self-contained clean-room rebuild blueprint chunk.

The downstream consumer will have no access to the original repository, files, or hidden context, so this output must be implementation-complete for the requested sections.

Global rules:
- Use only evidence provided here.
- Clearly distinguish evidence, inference, assumption, gap, and recommendation.
- Cite evidence paths or module references where practical.
- Do not copy source code.
- Return only the requested sections.

--- Repository File Tree ---
{tree_str}

--- Manifest / Config Evidence ---
{manifests_content[:12000]}

--- Component Syntheses ---
{specs_str[:22000]}

--- Structured Intermediate Analysis State ---
{analysis_state_markdown[:14000]}

--- Rolling Decisions From Earlier Sections ---
{rolling_state}

--- Target Task ---
{chunk_prompt}

Return only markdown for the requested sections.
"""


def build_repair_prompt(
    chunk_range: str,
    existing_output: str,
    issues: List[str],
) -> str:
    formatted_issues = "\n".join(f"- {issue}" for issue in issues)
    return f"""The previous blueprint output for {chunk_range} is incomplete or weak.

Problems to fix:
{formatted_issues}

Existing output:
{existing_output}

Rewrite the same section range to fix every issue while preserving clean-room constraints, evidence discipline, and implementation-ready detail.
Return only the rewritten markdown.
"""


def build_rolling_state_prompt(previous_output: str, current_state: str) -> str:
    return (
        "Current consolidated state:\n"
        f"{current_state}\n\n"
        "Newly generated section output:\n"
        f"{previous_output}\n\n"
        "Update the consolidated rolling state with durable architecture decisions, major features, entities, APIs, security requirements, gaps, and assumptions."
    )


def validate_section_output(section_output: str, required_headings: Iterable[str]) -> List[str]:
    issues: List[str] = []
    for heading in required_headings:
        if heading not in section_output:
            issues.append(f"Missing required heading: {heading}")
    lowered = section_output.lower()
    if "evidence" not in lowered:
        issues.append("Output does not visibly include evidence references.")
    if "assumption" not in lowered and "gap" not in lowered and "inference" not in lowered:
        issues.append("Output does not clearly distinguish assumptions, gaps, or inferences.")
    if len(section_output.strip()) < 1200:
        issues.append("Output is too short to be considered implementation-complete.")
    return issues

