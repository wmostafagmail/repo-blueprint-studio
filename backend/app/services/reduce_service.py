import json
import logging
from pathlib import Path
from typing import List, Dict, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed

from app.services.prompt_builders import (
    COMPONENT_SYSTEM_PROMPT,
    build_component_prompt,
)

logger = logging.getLogger(__name__)

class ReduceService:
    def __init__(
        self, 
        provider, 
        workspace_path: Path, 
        log_fn: Callable[[str, str], None], 
        progress_fn: Callable[[int, str], None]
    ):
        self.provider = provider
        self.workspace_path = workspace_path
        self.log = log_fn
        self.progress = progress_fn
        self.specs_dir = workspace_path / "components"
        self.specs_dir.mkdir(parents=True, exist_ok=True)

    def group_by_components(self, summaries: List[Dict]) -> Dict[str, List[Dict]]:
        """
        Groups file summaries by parent directory to define components.
        If a directory has subdirectories, it groups them cleanly.
        """
        groups = {}
        for s in summaries:
            path_str = s.get("path", "")
            if not path_str:
                continue
            
            # Extract parent directory as component name
            path_obj = Path(path_str)
            parts = path_obj.parts
            
            if len(parts) <= 1:
                component = "root"
            else:
                # Group by up to the first 2 directory segments (e.g. backend/app, frontend/src)
                component = "/".join(parts[:2])
                
            if component not in groups:
                groups[component] = []
            groups[component].append(s)
            
        return groups

    def synthesize_component(self, component_name: str, summaries: List[Dict]) -> str:
        """
        Sends the compiled summaries of a component to the LLM to create a component-level spec.
        """
        self.log(f"Synthesizing component spec for directory/module '{component_name}'...", "INFO")
        
        # Format file summaries for prompt
        formatted_files = []
        for s in summaries:
            p = s.get("path")
            t = s.get("type", "summary")
            if t == "raw":
                content = s.get("content", "")
                # Limit raw file size inside prompt to keep context small
                formatted_files.append(
                    f"File: {p} [Type: Critical Raw Code]\n"
                    f"```\n{content[:8000]}\n```"
                )
            elif t == "summary":
                resp = ", ".join(s.get("responsibilities", []))
                exp = ", ".join(s.get("exports", []))
                dep = ", ".join(s.get("dependencies", []))
                evidence = "; ".join(s.get("evidence", []))
                formatted_files.append(
                    f"File: {p} [Type: Summary]\n"
                    f" - Responsibilities: {resp}\n"
                    f" - Key Exports: {exp}\n"
                    f" - Imports/Deps: {dep}\n"
                    f" - Evidence: {evidence}"
                )
            else:
                formatted_files.append(
                    f"File: {p} [Type: Text]\n"
                    f"Content: {s.get('content', '')[:3000]}"
                )
                
        context_str = "\n\n".join(formatted_files)
        
        system_prompt = COMPONENT_SYSTEM_PROMPT
        prompt = build_component_prompt(component_name, context_str)
        
        try:
            resp = self.provider.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.2,
                max_tokens=1500
            )
            spec_content = resp.strip()
        except Exception as e:
            self.log(f"Synthesis failed for component {component_name}: {str(e)}", "WARNING")
            spec_content = f"Synthesis failed for component {component_name}: {str(e)}"

        # Save component spec
        escaped_name = component_name.replace("/", "_")
        target_file = self.specs_dir / f"{escaped_name}_spec.txt"
        target_file.write_text(spec_content, encoding="utf-8")
        
        return spec_content

    def reduce_summaries(self, summaries: List[Dict]) -> Dict[str, str]:
        """
        Coordinates the reduce phase, synthesizing all components.
        """
        groups = self.group_by_components(summaries)
        total_groups = len(groups)
        self.log(f"Found {total_groups} components to synthesize: {list(groups.keys())}", "INFO")
        
        synthesized_specs = {}
        completed = 0
        
        # Concurrency limit = 2 workers to prevent overloading local models
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = {
                executor.submit(self.synthesize_component, comp_name, comp_summaries): comp_name
                for comp_name, comp_summaries in groups.items()
            }
            
            for future in as_completed(futures):
                comp_name = futures[future]
                try:
                    spec = future.result()
                    synthesized_specs[comp_name] = spec
                except Exception as e:
                    self.log(f"Unhandled thread error during synthesis of {comp_name}: {str(e)}", "ERROR")
                    synthesized_specs[comp_name] = f"Synthesis error: {str(e)}"
                    
                completed += 1
                pct = int(50 + (completed / total_groups) * 15) # Scale from 50% to 65% overall progress
                self.progress(pct, f"Synthesizing component specs ({completed}/{total_groups} completed)")
                
        return synthesized_specs
