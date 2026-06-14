import json
import logging
from pathlib import Path
from typing import Callable, Dict, List

from app.services.prompt_builders import (
    ANALYSIS_STATE_SYSTEM_PROMPT,
    MASTER_SYSTEM_PROMPT,
    ROLLING_STATE_SYSTEM_PROMPT,
    SECTION_CHUNKS,
    build_analysis_state_prompt,
    build_repair_prompt,
    build_rolling_state_prompt,
    build_section_prompt,
    validate_section_output,
)

logger = logging.getLogger(__name__)


class IncrementalSpecGenerator:
    def __init__(
        self,
        provider,
        workspace_path: Path,
        log_fn: Callable[[str, str], None],
        progress_fn: Callable[[int, str], None],
    ):
        self.provider = provider
        self.workspace_path = workspace_path
        self.log = log_fn
        self.progress = progress_fn

    def build_analysis_state(
        self,
        repo_url: str,
        repo_name: str,
        file_tree: List[str],
        manifests_content: str,
        component_specs: Dict[str, str],
    ) -> Dict:
        self.log("Building structured intermediate analysis state from repository evidence...", "INFO")
        prompt = build_analysis_state_prompt(
            repo_name=repo_name,
            repo_url=repo_url,
            file_tree=file_tree,
            manifests_content=manifests_content,
            component_specs=component_specs,
        )
        try:
            resp = self.provider.generate(
                prompt=prompt,
                system_prompt=ANALYSIS_STATE_SYSTEM_PROMPT,
                temperature=0.1,
                max_tokens=2500,
            )
            cleaned = resp.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1]
            if cleaned.endswith("```"):
                cleaned = cleaned.rsplit("\n", 1)[0]
            if cleaned.startswith("json"):
                cleaned = cleaned.split("json", 1)[1]
            parsed = json.loads(cleaned.strip())
            self.log(
                "Structured state extracted: "
                f"{len(parsed.get('features', []))} features, "
                f"{len(parsed.get('entities', []))} entities, "
                f"{len(parsed.get('api_contracts', []))} API contracts, "
                f"{len(parsed.get('ui_surfaces', []))} UI surfaces.",
                "INFO",
            )
            return parsed
        except Exception as e:
            self.log(f"Failed to build structured analysis state: {str(e)}", "WARNING")
            return {
                "product_summary": "",
                "actors": [],
                "features": [],
                "entities": [],
                "api_contracts": [],
                "ui_surfaces": [],
                "security_findings": [],
                "operations_findings": [],
                "assumptions": [],
                "gaps": [f"Structured state extraction failed: {str(e)}"],
            }

    def format_analysis_state_markdown(self, analysis_state: Dict) -> str:
        def fmt_items(title: str, items: List[Dict]) -> str:
            if not items:
                return f"### {title}\n- None extracted.\n"
            lines = [f"### {title}"]
            for item in items[:20]:
                evidence = ", ".join(item.get("evidence", [])[:4])
                lines.append(
                    f"- {item.get('name', 'Unnamed')}: {item.get('summary', '')} "
                    f"(confidence: {item.get('confidence', 'medium')}; evidence: {evidence})"
                )
            return "\n".join(lines) + "\n"

        sections = [
            f"## Product Summary\n{analysis_state.get('product_summary', 'Not extracted.')}\n",
            fmt_items("Actors", analysis_state.get("actors", [])),
            fmt_items("Features", analysis_state.get("features", [])),
            fmt_items("Entities", analysis_state.get("entities", [])),
            fmt_items("API Contracts", analysis_state.get("api_contracts", [])),
            fmt_items("UI Surfaces", analysis_state.get("ui_surfaces", [])),
            fmt_items("Security Findings", analysis_state.get("security_findings", [])),
            fmt_items("Operations Findings", analysis_state.get("operations_findings", [])),
            "## Assumptions\n" + "\n".join(f"- {item}" for item in analysis_state.get("assumptions", [])[:12]) + "\n",
            "## Gaps\n" + "\n".join(f"- {item}" for item in analysis_state.get("gaps", [])[:12]) + "\n",
        ]
        return "\n".join(sections)

    def generate_rolling_state_summary(self, previous_output: str, current_state: str) -> str:
        prompt = build_rolling_state_prompt(previous_output, current_state)
        try:
            resp = self.provider.generate(
                prompt=prompt,
                system_prompt=ROLLING_STATE_SYSTEM_PROMPT,
                temperature=0.1,
                max_tokens=450,
            )
            return resp.strip()
        except Exception as e:
            self.log(f"Failed to update rolling architectural state: {str(e)}", "WARNING")
            return current_state

    def generate_blueprint(
        self,
        repo_url: str,
        repo_name: str,
        file_tree: List[str],
        manifests_content: str,
        component_specs: Dict[str, str],
    ) -> str:
        self.log("Starting quality-first staged rebuild blueprint generation...", "INFO")
        self.progress(66, "Extracting structured repository findings")

        analysis_state = self.build_analysis_state(
            repo_url=repo_url,
            repo_name=repo_name,
            file_tree=file_tree,
            manifests_content=manifests_content,
            component_specs=component_specs,
        )
        analysis_state_markdown = self.format_analysis_state_markdown(analysis_state)

        rolling_state = "No blueprint sections have been finalized yet."
        all_sections: List[str] = []
        total_chunks = len(SECTION_CHUNKS)

        for idx, chunk in enumerate(SECTION_CHUNKS):
            chunk_range = str(chunk["range_str"])
            self.log(f"Drafting {chunk_range} using the shared high-quality blueprint contract...", "INFO")
            self.progress(
                int(70 + (idx / total_chunks) * 18),
                f"Drafting blueprint {chunk_range}",
            )

            prompt = build_section_prompt(
                repo_name=repo_name,
                repo_url=repo_url,
                manifests_content=manifests_content,
                component_specs=component_specs,
                analysis_state_markdown=analysis_state_markdown,
                rolling_state=rolling_state,
                chunk_prompt=str(chunk["prompt"]),
                file_tree=file_tree,
            )
            resp = self.provider.generate(
                prompt=prompt,
                system_prompt=MASTER_SYSTEM_PROMPT,
                temperature=0.2,
                max_tokens=5000,
            )
            section_output = resp.strip()

            issues = validate_section_output(section_output, chunk["required_headings"])
            if issues:
                self.log(
                    f"Quality gate flagged {len(issues)} issue(s) for {chunk_range}. Running section repair pass...",
                    "WARNING",
                )
                repair_prompt = build_repair_prompt(chunk_range, section_output, issues)
                repaired = self.provider.generate(
                    prompt=repair_prompt,
                    system_prompt=MASTER_SYSTEM_PROMPT,
                    temperature=0.15,
                    max_tokens=5000,
                )
                repaired_output = repaired.strip()
                repaired_issues = validate_section_output(repaired_output, chunk["required_headings"])
                if not repaired_issues:
                    section_output = repaired_output
                    self.log(f"Repair pass completed successfully for {chunk_range}.", "INFO")
                else:
                    self.log(
                        f"Repair pass for {chunk_range} still left {len(repaired_issues)} issue(s); keeping best available draft.",
                        "WARNING",
                    )
            else:
                self.log(f"Quality gate passed for {chunk_range}.", "INFO")

            all_sections.append(section_output)
            if idx < total_chunks - 1:
                self.log(f"Updating rolling state after {chunk_range}...", "INFO")
                rolling_state = self.generate_rolling_state_summary(section_output, rolling_state)

        self.progress(92, "Assembling final rebuild blueprint")
        self.log("Assembling final rebuild blueprint from validated section chunks...", "INFO")
        return "\n\n---\n\n".join(all_sections)
