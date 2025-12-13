"""Language configuration for code analysis capability.

Provides consistent language handling across all tools:
- File extension mapping
- Exclude directories per language ecosystem
- Symbol extraction capabilities
- Comment patterns for each language
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from enum import Enum


class LanguageId(str, Enum):
    """Supported language identifiers."""
    PYTHON = "python"
    TYPESCRIPT = "typescript"
    JAVASCRIPT = "javascript"
    GO = "go"
    RUST = "rust"
    JAVA = "java"
    C = "c"
    CPP = "cpp"
    RUBY = "ruby"
    PHP = "php"


@dataclass
class LanguageSpec:
    """Specification for a programming language."""

    id: LanguageId
    name: str
    extensions: Set[str]
    exclude_dirs: Set[str]
    comment_single: str
    comment_multi_start: Optional[str] = None
    comment_multi_end: Optional[str] = None
    symbol_extraction: bool = True

    # Regex patterns for symbol extraction
    class_pattern: Optional[str] = None
    function_pattern: Optional[str] = None
    import_pattern: Optional[str] = None


LANGUAGE_SPECS: Dict[LanguageId, LanguageSpec] = {
    LanguageId.PYTHON: LanguageSpec(
        id=LanguageId.PYTHON,
        name="Python",
        extensions={".py", ".pyi", ".pyw"},
        exclude_dirs={"__pycache__", ".venv", "venv", ".pytest_cache", ".mypy_cache", ".tox", "egg-info"},
        comment_single="#",
        comment_multi_start='"""',
        comment_multi_end='"""',
        symbol_extraction=True,
        class_pattern=r"^\s*class\s+(\w+)",
        function_pattern=r"^\s*(?:async\s+)?def\s+(\w+)",
        import_pattern=r"^\s*(?:from\s+(\S+)\s+)?import\s+",
    ),
    LanguageId.TYPESCRIPT: LanguageSpec(
        id=LanguageId.TYPESCRIPT,
        name="TypeScript",
        extensions={".ts", ".tsx", ".mts", ".cts"},
        exclude_dirs={"node_modules", "dist", "build", ".next", ".nuxt"},
        comment_single="//",
        comment_multi_start="/*",
        comment_multi_end="*/",
        symbol_extraction=True,
        class_pattern=r"^\s*(?:export\s+)?(?:abstract\s+)?class\s+(\w+)",
        function_pattern=r"^\s*(?:export\s+)?(?:async\s+)?function\s+(\w+)",
        import_pattern=r'^\s*import\s+.*?from\s+[\'"]([^\'"]+)[\'"]',
    ),
    LanguageId.JAVASCRIPT: LanguageSpec(
        id=LanguageId.JAVASCRIPT,
        name="JavaScript",
        extensions={".js", ".jsx", ".mjs", ".cjs"},
        exclude_dirs={"node_modules", "dist", "build", ".next"},
        comment_single="//",
        comment_multi_start="/*",
        comment_multi_end="*/",
        symbol_extraction=True,
        class_pattern=r"^\s*(?:export\s+)?class\s+(\w+)",
        function_pattern=r"^\s*(?:export\s+)?(?:async\s+)?function\s+(\w+)",
        import_pattern=r'^\s*import\s+.*?from\s+[\'"]([^\'"]+)[\'"]',
    ),
    LanguageId.GO: LanguageSpec(
        id=LanguageId.GO,
        name="Go",
        extensions={".go"},
        exclude_dirs={"vendor", "bin", "pkg"},
        comment_single="//",
        comment_multi_start="/*",
        comment_multi_end="*/",
        symbol_extraction=True,
        class_pattern=r"^\s*type\s+(\w+)\s+struct",
        function_pattern=r"^\s*func\s+(?:\([^)]+\)\s+)?(\w+)",
        import_pattern=r'^\s*import\s+(?:\(\s*)?["\']([^"\']+)["\']',
    ),
    LanguageId.RUST: LanguageSpec(
        id=LanguageId.RUST,
        name="Rust",
        extensions={".rs"},
        exclude_dirs={"target", "debug", "release"},
        comment_single="//",
        comment_multi_start="/*",
        comment_multi_end="*/",
        symbol_extraction=True,
        class_pattern=r"^\s*(?:pub\s+)?struct\s+(\w+)",
        function_pattern=r"^\s*(?:pub\s+)?(?:async\s+)?fn\s+(\w+)",
        import_pattern=r"^\s*use\s+([^;]+)",
    ),
    LanguageId.JAVA: LanguageSpec(
        id=LanguageId.JAVA,
        name="Java",
        extensions={".java"},
        exclude_dirs={"target", "build", ".gradle", "out"},
        comment_single="//",
        comment_multi_start="/*",
        comment_multi_end="*/",
        symbol_extraction=True,
        class_pattern=r"^\s*(?:public\s+)?(?:abstract\s+)?class\s+(\w+)",
        function_pattern=r"^\s*(?:public|private|protected)?\s*(?:static\s+)?(?:\w+\s+)+(\w+)\s*\(",
        import_pattern=r"^\s*import\s+([^;]+)",
    ),
    LanguageId.C: LanguageSpec(
        id=LanguageId.C,
        name="C",
        extensions={".c", ".h"},
        exclude_dirs={"build", "obj", "bin"},
        comment_single="//",
        comment_multi_start="/*",
        comment_multi_end="*/",
        symbol_extraction=True,
        class_pattern=r"^\s*(?:typedef\s+)?struct\s+(\w+)",
        function_pattern=r"^\s*(?:\w+\s+)+(\w+)\s*\([^)]*\)\s*\{",
        import_pattern=r'^\s*#include\s+[<"]([^>"]+)[>"]',
    ),
    LanguageId.CPP: LanguageSpec(
        id=LanguageId.CPP,
        name="C++",
        extensions={".cpp", ".cc", ".cxx", ".hpp", ".hh", ".hxx", ".h"},
        exclude_dirs={"build", "obj", "bin", "cmake-build-debug", "cmake-build-release"},
        comment_single="//",
        comment_multi_start="/*",
        comment_multi_end="*/",
        symbol_extraction=True,
        class_pattern=r"^\s*(?:template\s*<[^>]*>\s*)?class\s+(\w+)",
        function_pattern=r"^\s*(?:\w+\s+)+(\w+)\s*\([^)]*\)\s*(?:const\s*)?\{",
        import_pattern=r'^\s*#include\s+[<"]([^>"]+)[>"]',
    ),
    LanguageId.RUBY: LanguageSpec(
        id=LanguageId.RUBY,
        name="Ruby",
        extensions={".rb", ".rake", ".gemspec"},
        exclude_dirs={"vendor", "bundle", ".bundle"},
        comment_single="#",
        comment_multi_start="=begin",
        comment_multi_end="=end",
        symbol_extraction=True,
        class_pattern=r"^\s*class\s+(\w+)",
        function_pattern=r"^\s*def\s+(\w+)",
        import_pattern=r"^\s*require\s+['\"]([^'\"]+)['\"]",
    ),
    LanguageId.PHP: LanguageSpec(
        id=LanguageId.PHP,
        name="PHP",
        extensions={".php", ".phtml"},
        exclude_dirs={"vendor", "cache"},
        comment_single="//",
        comment_multi_start="/*",
        comment_multi_end="*/",
        symbol_extraction=True,
        class_pattern=r"^\s*(?:abstract\s+)?class\s+(\w+)",
        function_pattern=r"^\s*(?:public|private|protected)?\s*function\s+(\w+)",
        import_pattern=r"^\s*(?:use|require|include)\s+([^;]+)",
    ),
}

COMMON_EXCLUDE_DIRS = {
    ".git",
    ".svn",
    ".hg",
    ".idea",
    ".vscode",
    ".DS_Store",
}


@dataclass
class LanguageConfig:
    """Combined language configuration for analysis."""

    languages: List[LanguageId] = field(default_factory=list)
    _specs: Dict[LanguageId, LanguageSpec] = field(default_factory=dict, repr=False)

    def __post_init__(self):
        """Load specs for selected languages."""
        if not self.languages:
            self.languages = list(LanguageId)

        for lang_id in self.languages:
            if lang_id in LANGUAGE_SPECS:
                self._specs[lang_id] = LANGUAGE_SPECS[lang_id]

    @property
    def code_extensions(self) -> Set[str]:
        """Get all code file extensions for configured languages."""
        extensions = set()
        for spec in self._specs.values():
            extensions.update(spec.extensions)
        return extensions

    @property
    def exclude_dirs(self) -> Set[str]:
        """Get all directories to exclude for configured languages."""
        dirs = COMMON_EXCLUDE_DIRS.copy()
        for spec in self._specs.values():
            dirs.update(spec.exclude_dirs)
        return dirs

    def supports_file(self, filename: str) -> bool:
        """Check if file is supported by configured languages."""
        from pathlib import Path
        suffix = Path(filename).suffix.lower()
        return suffix in self.code_extensions

    def get_language_for_file(self, filename: str) -> Optional[LanguageId]:
        """Get the language ID for a file."""
        from pathlib import Path
        suffix = Path(filename).suffix.lower()

        for lang_id, spec in self._specs.items():
            if suffix in spec.extensions:
                return lang_id
        return None

    def get_spec_for_file(self, filename: str) -> Optional[LanguageSpec]:
        """Get the language spec for a file."""
        lang_id = self.get_language_for_file(filename)
        if lang_id:
            return self._specs.get(lang_id)
        return None

    def should_exclude_dir(self, dirname: str) -> bool:
        """Check if directory should be excluded."""
        return dirname in self.exclude_dirs

    def get_symbol_patterns(self, filename: str) -> Dict[str, Optional[str]]:
        """Get symbol extraction patterns for a file."""
        spec = self.get_spec_for_file(filename)
        if spec:
            return {
                "class": spec.class_pattern,
                "function": spec.function_pattern,
                "import": spec.import_pattern,
            }
        return {"class": None, "function": None, "import": None}

    def to_dict(self) -> Dict:
        """Serialize config to dict."""
        return {
            "languages": [lang.value for lang in self.languages],
            "extensions": list(self.code_extensions),
            "exclude_dirs": list(self.exclude_dirs),
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "LanguageConfig":
        """Create config from dict."""
        languages = [LanguageId(lang) for lang in data.get("languages", [])]
        return cls(languages=languages)


_language_config: Optional[LanguageConfig] = None


def get_language_config(languages: Optional[List[str]] = None) -> LanguageConfig:
    """Get language configuration."""
    global _language_config

    if languages is not None:
        lang_ids = []
        for lang in languages:
            try:
                lang_ids.append(LanguageId(lang.lower()))
            except ValueError:
                pass
        return LanguageConfig(languages=lang_ids)

    if _language_config is None:
        _language_config = LanguageConfig()
    return _language_config


def set_language_config(languages: List[str]) -> LanguageConfig:
    """Set the global language configuration."""
    global _language_config
    lang_ids = []
    for lang in languages:
        try:
            lang_ids.append(LanguageId(lang.lower()))
        except ValueError:
            pass
    _language_config = LanguageConfig(languages=lang_ids)
    return _language_config


def detect_repo_languages(repo_path: str) -> List[LanguageId]:
    """Auto-detect languages in a repository."""
    from pathlib import Path

    indicators = {
        LanguageId.PYTHON: ["pyproject.toml", "setup.py", "requirements.txt", "Pipfile"],
        LanguageId.TYPESCRIPT: ["tsconfig.json", "package.json"],
        LanguageId.JAVASCRIPT: ["package.json", ".npmrc"],
        LanguageId.GO: ["go.mod", "go.sum"],
        LanguageId.RUST: ["Cargo.toml", "Cargo.lock"],
        LanguageId.JAVA: ["pom.xml", "build.gradle", "build.gradle.kts"],
        LanguageId.RUBY: ["Gemfile", "Rakefile", ".ruby-version"],
        LanguageId.PHP: ["composer.json", "composer.lock"],
        LanguageId.C: ["Makefile", "CMakeLists.txt"],
        LanguageId.CPP: ["CMakeLists.txt", "Makefile"],
    }

    repo = Path(repo_path)
    detected = set()

    for lang_id, files in indicators.items():
        for filename in files:
            if (repo / filename).exists():
                detected.add(lang_id)
                break

    for item in repo.iterdir():
        if item.is_file():
            for lang_id, spec in LANGUAGE_SPECS.items():
                if item.suffix.lower() in spec.extensions:
                    detected.add(lang_id)

    return list(detected) if detected else [LanguageId.PYTHON]
