from pathlib import Path
import os

IGNORE_DIRS = {
    ".git", "node_modules", "vendor", "dist", "build", ".next", ".nuxt",
    "coverage", ".cache", ".venv", "venv", "__pycache__", ".idea", ".vscode",
    ".DS_Store", "env", ".pytest_cache", ".mypy_cache", "target", "bin", "obj",
    "repo-spec-workspace", ".repo-spec-workspace"
}

MANIFEST_NAMES = {
    "package.json", "pnpm-lock.yaml", "yarn.lock", "package-lock.json",
    "requirements.txt", "pyproject.toml", "poetry.lock", "uv.lock", "Pipfile",
    "Cargo.toml", "go.mod", "pom.xml", "build.gradle", "composer.json", "Gemfile",
    "Dockerfile", "docker-compose.yml", "compose.yml", "Makefile", "tsconfig.json",
    "vite.config.ts", "vite.config.js", "next.config.js", "next.config.ts",
    "schema.prisma", "README.md", "README", "README.txt", ".env.example"
}

SOURCE_EXTENSIONS = {
    ".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".cs", ".go", ".rs", ".php",
    ".rb", ".swift", ".kt", ".kts", ".dart", ".c", ".cpp", ".h", ".hpp",
    ".vue", ".svelte", ".html", ".css", ".scss", ".sql", ".graphql", ".proto"
}

def should_ignore_path(path: Path) -> bool:
    """
    Returns True if the path contains any directory from IGNORE_DIRS.
    """
    return any(part in IGNORE_DIRS for part in path.parts)

def is_important_file(path: Path, rel_path_str: str) -> bool:
    """
    Checks if a file is highly important for architectural or package details.
    """
    name = path.name
    if name in MANIFEST_NAMES or rel_path_str in MANIFEST_NAMES:
        return True
    
    # Check if the path belongs to standard code directories
    parts = [p.lower() for p in path.parts]
    code_dirs = {"src", "app", "pages", "components", "routes", "controllers", "services", "models", "schemas", "migrations"}
    if any(cd in parts for cd in code_dirs):
        return path.suffix.lower() in SOURCE_EXTENSIONS
        
    return False
