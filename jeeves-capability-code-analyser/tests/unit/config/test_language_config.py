"""Tests for language configuration module."""

import pytest
from pathlib import Path

from jeeves_capability_code_analyser.config import (
    LanguageId,
    LanguageSpec,
    LanguageConfig,
    LANGUAGE_SPECS,
    get_language_config,
    set_language_config,
    detect_repo_languages,
)


class TestLanguageSpec:
    """Tests for LanguageSpec dataclass."""

    def test_python_spec_exists(self):
        """Python spec should be defined."""
        assert LanguageId.PYTHON in LANGUAGE_SPECS
        spec = LANGUAGE_SPECS[LanguageId.PYTHON]
        assert ".py" in spec.extensions
        assert "__pycache__" in spec.exclude_dirs

    def test_go_spec_exists(self):
        """Go spec should be defined."""
        assert LanguageId.GO in LANGUAGE_SPECS
        spec = LANGUAGE_SPECS[LanguageId.GO]
        assert ".go" in spec.extensions
        assert "vendor" in spec.exclude_dirs

    def test_rust_spec_exists(self):
        """Rust spec should be defined."""
        assert LanguageId.RUST in LANGUAGE_SPECS
        spec = LANGUAGE_SPECS[LanguageId.RUST]
        assert ".rs" in spec.extensions
        assert "target" in spec.exclude_dirs

    def test_all_specs_have_patterns(self):
        """All specs should have symbol extraction patterns."""
        for lang_id, spec in LANGUAGE_SPECS.items():
            assert spec.class_pattern is not None, f"{lang_id} missing class_pattern"
            assert spec.function_pattern is not None, f"{lang_id} missing function_pattern"


class TestLanguageConfig:
    """Tests for LanguageConfig class."""

    def test_default_config_includes_all_languages(self):
        """Default config should include all languages."""
        config = LanguageConfig()
        assert len(config.languages) == len(LanguageId)

    def test_specific_languages_config(self):
        """Config with specific languages should only include those."""
        config = LanguageConfig(languages=[LanguageId.PYTHON, LanguageId.GO])
        assert len(config.languages) == 2
        assert ".py" in config.code_extensions
        assert ".go" in config.code_extensions
        assert ".rs" not in config.code_extensions

    def test_code_extensions_combined(self):
        """Extensions should be combined from all configured languages."""
        config = LanguageConfig(languages=[LanguageId.PYTHON, LanguageId.TYPESCRIPT])
        assert ".py" in config.code_extensions
        assert ".ts" in config.code_extensions
        assert ".tsx" in config.code_extensions

    def test_exclude_dirs_combined(self):
        """Exclude dirs should be combined from all configured languages."""
        config = LanguageConfig(languages=[LanguageId.PYTHON, LanguageId.JAVASCRIPT])
        assert "__pycache__" in config.exclude_dirs
        assert "node_modules" in config.exclude_dirs
        assert ".git" in config.exclude_dirs

    def test_supports_file(self):
        """Should correctly identify supported files."""
        config = LanguageConfig(languages=[LanguageId.PYTHON])
        assert config.supports_file("main.py")
        assert config.supports_file("tests/test_foo.py")
        assert not config.supports_file("main.go")
        assert not config.supports_file("main.rs")

    def test_get_language_for_file(self):
        """Should return correct language for file."""
        config = LanguageConfig()
        assert config.get_language_for_file("main.py") == LanguageId.PYTHON
        assert config.get_language_for_file("main.go") == LanguageId.GO
        assert config.get_language_for_file("main.rs") == LanguageId.RUST
        assert config.get_language_for_file("main.ts") == LanguageId.TYPESCRIPT
        assert config.get_language_for_file("main.txt") is None

    def test_should_exclude_dir(self):
        """Should correctly identify excluded directories."""
        config = LanguageConfig(languages=[LanguageId.PYTHON, LanguageId.GO])
        assert config.should_exclude_dir(".git")
        assert config.should_exclude_dir("__pycache__")
        assert config.should_exclude_dir("vendor")
        assert not config.should_exclude_dir("src")
        assert not config.should_exclude_dir("lib")

    def test_get_symbol_patterns(self):
        """Should return correct patterns for files."""
        config = LanguageConfig()

        patterns = config.get_symbol_patterns("main.py")
        assert patterns["class"] is not None
        assert patterns["function"] is not None

        patterns = config.get_symbol_patterns("main.go")
        assert patterns["class"] is not None
        assert patterns["function"] is not None

        patterns = config.get_symbol_patterns("main.txt")
        assert patterns["class"] is None
        assert patterns["function"] is None

    def test_to_dict_from_dict(self):
        """Should serialize and deserialize correctly."""
        config = LanguageConfig(languages=[LanguageId.PYTHON, LanguageId.GO])
        data = config.to_dict()

        assert "python" in data["languages"]
        assert "go" in data["languages"]
        assert ".py" in data["extensions"]
        assert ".go" in data["extensions"]

        config2 = LanguageConfig.from_dict(data)
        assert config2.languages == config.languages


class TestGetLanguageConfig:
    """Tests for get_language_config function."""

    def test_returns_default_config(self):
        """Should return default config when no languages specified."""
        config = get_language_config()
        assert len(config.languages) > 0

    def test_returns_specific_config(self):
        """Should return config for specific languages."""
        config = get_language_config(["python", "go"])
        assert LanguageId.PYTHON in config.languages
        assert LanguageId.GO in config.languages
        assert LanguageId.RUST not in config.languages

    def test_handles_unknown_languages(self):
        """Should skip unknown language names."""
        config = get_language_config(["python", "unknown_lang", "go"])
        assert LanguageId.PYTHON in config.languages
        assert LanguageId.GO in config.languages
        assert len(config.languages) == 2


class TestSetLanguageConfig:
    """Tests for set_language_config function."""

    def test_sets_global_config(self):
        """Should set global configuration."""
        set_language_config(["rust", "go"])
        config = get_language_config()
        assert LanguageId.RUST in config.languages
        assert LanguageId.GO in config.languages

        set_language_config([l.value for l in LanguageId])


class TestDetectRepoLanguages:
    """Tests for detect_repo_languages function."""

    def test_detects_from_indicator_files(self, tmp_path):
        """Should detect languages from indicator files."""
        (tmp_path / "pyproject.toml").touch()
        detected = detect_repo_languages(str(tmp_path))
        assert LanguageId.PYTHON in detected

    def test_detects_from_code_files(self, tmp_path):
        """Should detect languages from code file extensions."""
        (tmp_path / "main.go").touch()
        detected = detect_repo_languages(str(tmp_path))
        assert LanguageId.GO in detected

    def test_detects_multiple_languages(self, tmp_path):
        """Should detect multiple languages."""
        (tmp_path / "pyproject.toml").touch()
        (tmp_path / "go.mod").touch()
        (tmp_path / "Cargo.toml").touch()
        detected = detect_repo_languages(str(tmp_path))
        assert LanguageId.PYTHON in detected
        assert LanguageId.GO in detected
        assert LanguageId.RUST in detected

    def test_defaults_to_python(self, tmp_path):
        """Should default to Python when nothing detected."""
        detected = detect_repo_languages(str(tmp_path))
        assert LanguageId.PYTHON in detected


class TestSymbolPatterns:
    """Tests for regex patterns in language specs."""

    def test_python_class_pattern(self):
        """Python class pattern should match correctly."""
        import re
        pattern = re.compile(LANGUAGE_SPECS[LanguageId.PYTHON].class_pattern)
        assert pattern.match("class Foo:").group(1) == "Foo"
        assert pattern.match("class FooBar(Base):").group(1) == "FooBar"
        assert pattern.match("  class Indented:").group(1) == "Indented"
        assert pattern.match("def not_a_class():") is None

    def test_python_function_pattern(self):
        """Python function pattern should match correctly."""
        import re
        pattern = re.compile(LANGUAGE_SPECS[LanguageId.PYTHON].function_pattern)
        assert pattern.match("def foo():").group(1) == "foo"
        assert pattern.match("async def bar():").group(1) == "bar"
        assert pattern.match("  def indented():").group(1) == "indented"
        assert pattern.match("class NotAFunc:") is None

    def test_go_struct_pattern(self):
        """Go struct pattern should match correctly."""
        import re
        pattern = re.compile(LANGUAGE_SPECS[LanguageId.GO].class_pattern)
        assert pattern.match("type Foo struct {").group(1) == "Foo"
        assert pattern.match("type Bar struct{").group(1) == "Bar"

    def test_go_function_pattern(self):
        """Go function pattern should match correctly."""
        import re
        pattern = re.compile(LANGUAGE_SPECS[LanguageId.GO].function_pattern)
        assert pattern.match("func main() {").group(1) == "main"
        assert pattern.match("func (s *Server) Start() {").group(1) == "Start"

    def test_rust_struct_pattern(self):
        """Rust struct pattern should match correctly."""
        import re
        pattern = re.compile(LANGUAGE_SPECS[LanguageId.RUST].class_pattern)
        assert pattern.match("struct Foo {").group(1) == "Foo"
        assert pattern.match("pub struct Bar {").group(1) == "Bar"

    def test_rust_function_pattern(self):
        """Rust function pattern should match correctly."""
        import re
        pattern = re.compile(LANGUAGE_SPECS[LanguageId.RUST].function_pattern)
        assert pattern.match("fn main() {").group(1) == "main"
        assert pattern.match("pub fn new() {").group(1) == "new"
        assert pattern.match("pub async fn fetch() {").group(1) == "fetch"
