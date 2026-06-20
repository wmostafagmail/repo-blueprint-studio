import json
import logging
import re
from pathlib import Path
from typing import Callable, Dict, List, Optional

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

BLUEPRINT_PROGRESS_ANALYSIS_STATE = 87
BLUEPRINT_PROGRESS_SECTION_START = 89
BLUEPRINT_PROGRESS_SECTION_END = 96
BLUEPRINT_PROGRESS_ASSEMBLY = 97


class IncrementalSpecGenerator:
    def __init__(
        self,
        provider,
        workspace_path: Path,
        log_fn: Callable[[str, str], None],
        progress_fn: Callable[[int, str], None],
        section_status_fn: Optional[Callable[[str, int, str, str], None]] = None,
    ):
        self.provider = provider
        self.workspace_path = workspace_path
        self.log = log_fn
        self.progress = progress_fn
        self.section_status = section_status_fn or (lambda section_id, progress, step, status="running": None)
        self.analysis_dir = workspace_path / "analysis"
        self.sections_dir = workspace_path / "sections"
        self.analysis_dir.mkdir(parents=True, exist_ok=True)
        self.sections_dir.mkdir(parents=True, exist_ok=True)

    def _save_text_artifact(self, relative_path: str, content: str):
        target = self.workspace_path / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    def _clean_llm_text(self, text: str) -> str:
        cleaned = (text or "").strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else ""
        if cleaned.endswith("```"):
            cleaned = cleaned.rsplit("\n", 1)[0]
        cleaned = cleaned.strip()
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:].strip()
        return cleaned

    def _extract_json_object(self, text: str) -> Dict:
        cleaned = self._clean_llm_text(text)
        if not cleaned:
            raise ValueError("Model returned an empty response")
        try:
            return json.loads(cleaned)
        except Exception:
            pass

        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            candidate = cleaned[start:end + 1]
            return json.loads(candidate)

        raise ValueError("No valid JSON object found in model response")

    def _repair_analysis_state_response(self, raw_response: str) -> Dict:
        self.provider.raise_if_cancelled()
        repair_prompt = (
            "The previous response was intended to be valid JSON but was malformed.\n\n"
            "Return only valid JSON matching the required analysis-state schema.\n"
            "Do not include markdown fences or commentary.\n\n"
            f"Malformed response:\n{raw_response}"
        )
        repaired = self.provider.generate(
            prompt=repair_prompt,
            system_prompt=ANALYSIS_STATE_SYSTEM_PROMPT,
            temperature=0.0,
            max_tokens=2500,
        )
        return self._extract_json_object(repaired)

    def _build_section_fallback(self, chunk_range: str, required_headings: List[str], issues: List[str], draft: str) -> str:
        issue_lines = "\n".join(f"- {issue}" for issue in issues)
        sections = []
        for heading in required_headings:
            if heading in draft:
                continue
            sections.append(
                f"{heading}\n\n"
                "Evidence: The model did not return a reliable section body for this heading in the current pass.\n\n"
                "Inference: Rebuild details for this heading should be derived from the shared analysis state, manifests, and component evidence.\n\n"
                "Assumption: This placeholder section was inserted to preserve blueprint structure after a low-confidence local-model response.\n\n"
                "Gap: A stronger rerun or a larger-capacity model is recommended for this section.\n"
            )
        if "Evidence" not in draft:
            sections.append("## Evidence Recovery Note\n\nEvidence: The generated draft omitted explicit evidence labeling, so a structural fallback note was added.\n")
        if "Assumption" not in draft and "Inference" not in draft and "Gap" not in draft:
            sections.append(
                "## Recovery Notes\n\n"
                "Inference: The local model returned an incomplete section draft.\n\n"
                "Assumption: A later compile or retry pass should strengthen this content.\n\n"
                f"Gap: Outstanding validation issues were:\n{issue_lines}\n"
            )
        base = draft.strip()
        additions = "\n\n".join(sections).strip()
        if not base:
            return additions
        if not additions:
            return base
        return f"{base}\n\n{additions}"

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
            self.provider.raise_if_cancelled()
            resp = self.provider.generate(
                prompt=prompt,
                system_prompt=ANALYSIS_STATE_SYSTEM_PROMPT,
                temperature=0.1,
                max_tokens=2500,
            )
            try:
                parsed = self._extract_json_object(resp)
            except Exception:
                self.log("Initial structured analysis state response was not valid JSON. Running JSON repair pass...", "WARNING")
                parsed = self._repair_analysis_state_response(resp)
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
        self.provider.raise_if_cancelled()
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
        self.progress(BLUEPRINT_PROGRESS_ANALYSIS_STATE, "Extracting structured repository findings")

        analysis_state = self.build_analysis_state(
            repo_url=repo_url,
            repo_name=repo_name,
            file_tree=file_tree,
            manifests_content=manifests_content,
            component_specs=component_specs,
        )
        self._save_text_artifact(
            "analysis/analysis_state.json",
            json.dumps(analysis_state, indent=2),
        )
        analysis_state_markdown = self.format_analysis_state_markdown(analysis_state)
        self._save_text_artifact("analysis/analysis_state.md", analysis_state_markdown)

        rolling_state = "No blueprint sections have been finalized yet."
        all_sections: List[str] = []
        total_chunks = len(SECTION_CHUNKS)

        for idx, chunk in enumerate(SECTION_CHUNKS):
            section_id = str(chunk["id"])
            chunk_range = str(chunk["range_str"])
            section_file_name = f"{idx + 1:02d}_{section_id}.md"
            self.section_status(section_id, 0, f"Queued {chunk_range}", "queued")
            self.log(f"Drafting {chunk_range} using the shared high-quality blueprint contract...", "INFO")
            self.progress(
                int(
                    BLUEPRINT_PROGRESS_SECTION_START
                    + (idx / total_chunks) * (BLUEPRINT_PROGRESS_SECTION_END - BLUEPRINT_PROGRESS_SECTION_START)
                ),
                f"Drafting blueprint section {idx + 1}/{total_chunks} ({chunk_range})",
            )
            self.section_status(section_id, 15, f"Drafting {chunk_range}", "running")

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
            self.provider.raise_if_cancelled()
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
                    f"Validation issues for {chunk_range}: {', '.join(issues)}",
                    "WARNING",
                )
                self.log(
                    f"Quality gate flagged {len(issues)} issue(s) for {chunk_range}. Running section repair pass...",
                    "WARNING",
                )
                self.progress(
                    min(BLUEPRINT_PROGRESS_SECTION_END, BLUEPRINT_PROGRESS_SECTION_START + idx + 1),
                    f"Repairing blueprint section {idx + 1}/{total_chunks} ({chunk_range})",
                )
                self.section_status(section_id, 70, f"Repairing {chunk_range}", "running")
                repair_prompt = build_repair_prompt(chunk_range, section_output, issues)
                self.provider.raise_if_cancelled()
                repaired = self.provider.generate(
                    prompt=repair_prompt,
                    system_prompt=MASTER_SYSTEM_PROMPT,
                    temperature=0.15,
                    max_tokens=5000,
                )
                repaired_output = repaired.strip()
                repaired_issues = validate_section_output(repaired_output, chunk["required_headings"])
                if len(repaired_issues) < len(issues):
                    section_output = repaired_output
                    issues = repaired_issues
                if not issues:
                    self.log(f"Repair pass completed successfully for {chunk_range}.", "INFO")
                else:
                    self.log(
                        f"Repair pass for {chunk_range} still left {len(issues)} issue(s); applying structural fallback for missing requirements.",
                        "WARNING",
                    )
                    section_output = self._build_section_fallback(
                        chunk_range,
                        list(chunk["required_headings"]),
                        issues,
                        section_output,
                    )
            else:
                self.log(f"Quality gate passed for {chunk_range}.", "INFO")

            all_sections.append(section_output)
            self._save_text_artifact(f"sections/{section_file_name}", section_output)
            self.section_status(section_id, 100, f"Completed {chunk_range}", "completed")
            if idx < total_chunks - 1:
                self.log(f"Updating rolling state after {chunk_range}...", "INFO")
                self.progress(
                    min(BLUEPRINT_PROGRESS_SECTION_END, BLUEPRINT_PROGRESS_SECTION_START + idx + 1),
                    f"Refreshing architectural state after section {idx + 1}/{total_chunks}",
                )
                rolling_state = self.generate_rolling_state_summary(section_output, rolling_state)

        self.progress(BLUEPRINT_PROGRESS_ASSEMBLY, "Assembling final rebuild blueprint")
        self.log("Assembling final rebuild blueprint from validated section chunks...", "INFO")
        compiled = "\n\n---\n\n".join(all_sections)
        self._save_text_artifact("sections/compiled_blueprint.md", compiled)
        return compiled
