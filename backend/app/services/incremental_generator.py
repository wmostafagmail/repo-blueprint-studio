import logging
from pathlib import Path
from typing import List, Dict, Callable

logger = logging.getLogger(__name__)

# Define the section chunks
SECTION_CHUNKS = [
    {
        "id": 1,
        "range_str": "Sections 1 to 5",
        "description": "1. Executive Summary, 2. Product Purpose and Scope, 3. Repository Evidence Summary, 4. Technology Stack, 5. Architecture Overview.",
        "prompt": (
            "Write Sections 1 to 5 of the rebuild blueprint specification:\n"
            "Section 1. Executive Summary: High level summary of what this repository does.\n"
            "Section 2. Product Purpose and Scope: Target problems and target users.\n"
            "Section 3. Repository Evidence Summary: List structural files and manifestations found.\n"
            "Section 4. Technology Stack: Primary languages, database choice, and frameworks.\n"
            "Section 5. Architecture Overview: Component layout and design patterns. "
            "You MUST include a valid Mermaid flowchart diagram (using ```mermaid ... ``` fences) "
            "that shows the high-level component architecture with data flow arrows. "
            "Example format: ```mermaid\nflowchart TD\n    A[Component A] -->|action| B[Component B]\n```"
        )
    },
    {
        "id": 2,
        "range_str": "Sections 6 to 10",
        "description": "6. Low-Level Design, 7. Functional Requirements, 8. User Roles and Permissions, 9. User Journeys and Workflows, 10. UI/UX Specification.",
        "prompt": (
            "Write Sections 6 to 10 of the rebuild blueprint specification:\n"
            "Section 6. Low-Level Design: Key classes, modules, and interfaces.\n"
            "Section 7. Functional Requirements: Core functionalities implemented.\n"
            "Section 8. User Roles and Permissions: Defined access levels.\n"
            "Section 9. User Journeys and Workflows: Critical workflow steps.\n"
            "Section 10. UI/UX Specification: Visual components, page layouts, or CLI interfaces."
        )
    },
    {
        "id": 3,
        "range_str": "Sections 11 to 15",
        "description": "11. API Specification, 12. Data Model and Database Design, 13. Business Rules and Validation Logic, 14. Integrations and External Services, 15. Security Specification.",
        "prompt": (
            "Write Sections 11 to 15 of the rebuild blueprint specification:\n"
            "Section 11. API Specification: REST routes, WebSockets, or CLI inputs/outputs.\n"
            "Section 12. Data Model and Database Design: Table schemas, collections, or state layouts. "
            "You MUST include a valid Mermaid erDiagram (using ```mermaid ... ``` fences) "
            "showing the key entities and their relationships. "
            "Example format: ```mermaid\nerDiagram\n    ENTITY_A ||--o{ ENTITY_B : has\n    ENTITY_A { int id PK }\n```\n"
            "Section 13. Business Rules and Validation Logic: Strict validation rules and domain logic constraints.\n"
            "Section 14. Integrations and External Services: Third-party SDKs, emails, or payment gateways.\n"
            "Section 15. Security Specification: Auth mechanisms, JWT, encryption, or CORS policies."
        )
    },
    {
        "id": 4,
        "range_str": "Sections 16 to 20",
        "description": "16. Performance and Scalability Specification, 17. Reliability and Error Handling, 18. Configuration and Environment Variables, 19. File Storage and Generated Assets, 20. Testing Strategy.",
        "prompt": (
            "Write Sections 16 to 20 of the rebuild blueprint specification:\n"
            "Section 16. Performance and Scalability Specification: Caching, database indexing, or optimization rules.\n"
            "Section 17. Reliability and Error Handling: Error codes, retries, and failure boundaries.\n"
            "Section 18. Configuration and Environment Variables: Settings keys, default values, and structure.\n"
            "Section 19. File Storage and Generated Assets: Upload paths, storage buckets, or local asset folders.\n"
            "Section 20. Testing Strategy: Unit tests, integration tests, or mock databases used."
        )
    },
    {
        "id": 5,
        "range_str": "Sections 21 to 25",
        "description": "21. Deployment and Operations, 22. Rebuild Implementation Plan, 23. Acceptance Criteria, 24. Risks, Gaps, Unknowns, and Assumptions, 25. Clean-Room Notes.",
        "prompt": (
            "Write Sections 21 to 25 of the rebuild blueprint specification:\n"
            "Section 21. Deployment and Operations: Dockerfiles, CI workflows, or hosting targets.\n"
            "Section 22. Rebuild Implementation Plan: Step-by-step phases to rebuild this codebase from scratch.\n"
            "Section 23. Acceptance Criteria: Checklist for a successful rebuild verification.\n"
            "Section 24. Risks, Gaps, Unknowns, and Assumptions: Ambiguities or missing evidence.\n"
            "Section 25. Clean-Room Notes: Explicit rebuild instructions, warnings, or best practices."
        )
    }
]

class IncrementalSpecGenerator:
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

    def generate_rolling_state_summary(self, previous_output: str, current_state: str) -> str:
        """
        Synthesizes/condenses the design choices made in the newly generated sections
        to update the rolling architectural state (ADR).
        """
        system_prompt = (
            "You are an expert technical editor. Summarize the core architectural design and implementation choices "
            "described in the text below into a 3-sentence summary. Focus on technology choice, database setup, "
            "routes, and design patterns. Do not write conversational preamble."
        )
        
        prompt = (
            f"Current saved state so far:\n{current_state}\n\n"
            f"New section details:\n{previous_output}\n\n"
            f"Update the architectural design summary:"
        )
        
        try:
            resp = self.provider.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.1,
                max_tokens=250
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
        component_specs: Dict[str, str]
    ) -> str:
        """
        Iteratively generates the 25-section spec, 5 sections at a time.
        """
        self.log("Starting Stage 3: Incremental Rebuild Blueprint Generation...", "INFO")
        
        # Format general metadata
        tree_str = "\n".join(file_tree[:200]) # Cap at 200 lines to keep context small
        if len(file_tree) > 200:
            tree_str += f"\n... ({len(file_tree) - 200} more files)"
            
        specs_str = ""
        for comp, spec in component_specs.items():
            specs_str += f"=== Component: {comp} ===\n{spec}\n\n"
            
        rolling_state = "No architectural choices resolved yet."
        all_sections = []
        
        total_chunks = len(SECTION_CHUNKS)
        
        for idx, chunk in enumerate(SECTION_CHUNKS):
            self.log(f"Generating {chunk['range_str']} ({chunk['description']})...", "INFO")
            
            system_prompt = (
                "You are an expert software architect building a clean-room specification blueprint to rebuild a repository.\n"
                "Write only the requested sections directly. Do not include introductory comments, concluding remarks, or chat filler.\n"
                "When sections require Mermaid diagrams, generate syntactically valid Mermaid code inside ```mermaid ... ``` fences. "
                "Diagrams must reflect the ACTUAL components found in the repository — do not use generic placeholder names."
            )
            
            prompt = (
                f"Repository: {repo_name}\n"
                f"Repository URL: {repo_url}\n\n"
                f"--- Overall File Tree ---\n"
                f"{tree_str}\n\n"
                f"--- Core Manifest / Config Content ---\n"
                f"{manifests_content[:10000]}\n\n" # Cap manifests at 10k chars
                f"--- Component Syntheses Specs ---\n"
                f"{specs_str[:15000]}\n\n" # Cap specs at 15k chars
                f"--- Rolling Design Choices Decided So Far ---\n"
                f"{rolling_state}\n\n"
                f"--- Target Task ---\n"
                f"{chunk['prompt']}\n\n"
                f"Output the sections in markdown format:"
            )
            
            try:
                resp = self.provider.generate(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    temperature=0.2,
                    max_tokens=4000
                )
                section_output = resp.strip()
                all_sections.append(section_output)
            except Exception as e:
                self.log(f"Failed to generate {chunk['range_str']}: {str(e)}", "ERROR")
                raise Exception(f"Incremental generation failed on {chunk['range_str']}: {str(e)}")

            # Update rolling architectural choices if not on the last chunk
            if idx < total_chunks - 1:
                self.log("Updating rolling architectural decisions state...", "INFO")
                rolling_state = self.generate_rolling_state_summary(section_output, rolling_state)
                self.log(f"Updated Rolling State: {rolling_state}", "DEBUG")
                
            # Progress scale: from 65% to 90%
            pct = int(65 + ((idx + 1) / total_chunks) * 25)
            self.progress(pct, f"Generating blueprint ({chunk['range_str']} complete)")

        self.log("All 5 blueprint chunks generated successfully.", "INFO")
        
        # Assemble final document
        blueprint = "\n\n---\n\n".join(all_sections)
        return blueprint
