from typing import List
import re
from datetime import datetime, timezone
from backend.app.services.providers.base import BaseLLMProvider

class MockProvider(BaseLLMProvider):
    def __init__(self, api_key: str = "", base_url: str = "", model: str = ""):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model

    def validate_settings(self) -> bool:
        return True

    def list_models(self) -> List[str]:
        return ["mock-model-v1", "mock-model-v2"]

    def generate(self, prompt: str, system_prompt: str, temperature: float = 0.2, max_tokens: int = 4000) -> str:
        # Try to extract repo name from prompt
        repo_name_match = re.search(r"(?:Repository:|Repo Name:|repo_name)\s*[:`]*\s*([a-zA-Z0-9_\-\.]+)", prompt, re.IGNORECASE)
        repo_name = repo_name_match.group(1) if repo_name_match else "mock-repo"
        
        # Try to extract repo url
        repo_url_match = re.search(r"https://github.com/[^\s`']+", prompt)
        repo_url = repo_url_match.group(0) if repo_url_match else f"https://github.com/mock-org/{repo_name}"

        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        
        template = """# {repo_name} Rebuild Blueprint

> Generated via Mock LLM Provider for clean-room reverse engineering.

## 0. Generation Metadata
| Field | Value |
|---|---|
| Repository | `{repo_name}` |
| Source | `{repo_url}` |
| Generated At UTC | `{now}` |
| Provider | `Mock LLM Provider` |
| Confidence | High (Mock Output) |

## 1. Executive Summary
This is a clean-room specification designed to reconstruct the `{repo_name}` repository. The repository appears to be a functional prototype/application containing basic routing, domain logic, and configurations. The rebuild target aims for 100% functional parity using modern standards and clean architectures.

## 2. Product Purpose and Scope
The product provides a system to manage domain-specific resources and workflows. It is scoped to run in local environments or be deployed as a containerized web application.

## 3. Repository Evidence Summary
- `README.md`: Explains installation and basic running instructions.
- `package.json` / `requirements.txt`: Outlines standard dependency managers.
- `src/` / `app/` structure: Houses source files for modular architecture.

## 4. Technology Stack
- **Backend**: Python 3.11 / FastAPI (or Node.js depending on the source structure)
- **Frontend**: React / Vite / TypeScript
- **Database**: SQLite for local data store

## 5. Architecture Overview
The application follows a standard Tier-3 architecture pattern:
```mermaid
flowchart TD
    Client[React Frontend] -->|API Calls| API[FastAPI Backend]
    API -->|Read/Write| DB[(SQLite Database)]
```

## 6. Low-Level Design
The system has modular layers consisting of:
- **Routes / Controllers**: Receive requests, validate models.
- **Services**: Implement core business validation.
- **DataAccess / Models**: Manage query building and entity mapping.

## 7. Functional Requirements
1. **User Management**: Creating accounts, retrieving profile info.
2. **Resource Catalog**: Listing, searching, and managing catalog items.
3. **Audit Trail**: Logging critical operations for safety.

## 8. User Roles and Permissions
- **Admin**: Full privileges to edit system configurations and manage all users.
- **User**: Standard read/write access to own created resources.
- **Guest**: Read-only access to public directory/assets.

## 9. User Journeys and Workflows
1. **Onboarding**: Guest signs up, receives confirmation, redirects to dashboard.
2. **Item Creation**: User fills forms, client validates inputs, triggers POST API, dashboard refreshes.

## 10. UI/UX Specification
- **Theme**: Premium light mode with slate accents, Outfit font.
- **Screens**:
  - `Home`: Dashboard summary.
  - `Details`: Item drilldown showing metrics and configurations.

## 11. API Specification
- `GET /api/health`: Returns service status.
- `POST /api/items`: Creates new catalog items. Expects JSON body; returns 201 Created.

## 12. Data Model and Database Design
```mermaid
erDiagram
    USERS ||--o{ ITEMS : owns
    USERS {
        int id PK
        string email UNIQUE
        string password_hash
    }
    ITEMS {
        int id PK
        string name
        int owner_id FK
    }
```

## 13. Business Rules and Validation Logic
- Item names must be alphanumeric and between 3 to 100 characters.
- User email addresses must match standardized regex formats.

## 14. Integrations and External Services
- No complex third-party external integrations detected in baseline repository.

## 15. Security Specification
- Passwords must be hashed using bcrypt or Argon2.
- JWT tokens are issued on successful authentication and checked via authorization headers.

## 16. Performance and Scalability Specification
- Page load latency should remain under 200ms for standard catalog queries.
- Limit payload sizes to a maximum of 5MB.

## 17. Reliability and Error Handling
- Exceptions are caught globally by app middleware and mapped to standardized JSON error payloads: { "error": "Message" }.

## 18. Configuration and Environment Variables
- `DATABASE_URL`: Connection string.
- `JWT_SECRET`: Used to sign web tokens.

## 19. File Storage and Generated Assets
- Uploaded user assets are stored in the local `./uploads` directory or mapped to bucket storage paths in production.

## 20. Testing Strategy
- Core endpoints must have 80%+ unit test coverage using Pytest or Jest.
- Integrate automated endpoint checks in Github Actions workflows.

## 21. Deployment and Operations
- Deployable as a single Docker container containing both web assets and API services.

## 22. Rebuild Implementation Plan
- **Milestone 1**: Scaffolding and DB schema set up.
- **Milestone 2**: Backend endpoints and testing.
- **Milestone 3**: UI design system integration.

## 23. Acceptance Criteria
- All frontend routes navigate correctly without console errors.
- Authentication returns valid JWTs and rejects invalid user credentials.

## 24. Risks, Gaps, Unknowns, and Assumptions
- *Assumption*: SQLite is sufficient for the target local deployment scale.
- *Gap*: Detailed background worker tasks were not identified in static manifests.

## 25. Clean-Room Notes
- DO NOT copy original code fragments.
- Follow the schemas and route patterns defined above to reconstruct functionally identical APIs.
"""
        return template.replace("{repo_name}", repo_name).replace("{repo_url}", repo_url).replace("{now}", now)
