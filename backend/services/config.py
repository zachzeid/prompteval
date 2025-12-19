"""Configuration loader for heuristic analysis rules."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


# Default config path
DEFAULT_CONFIG_PATH = Path(__file__).parent.parent.parent / "config" / "default_rules.yaml"


@dataclass
class AnalysisConfig:
    """Configuration for heuristic analysis.

    Can be loaded from YAML files for customization.
    """

    # Thresholds
    min_word_count: int = 20
    max_sentence_length: int = 40

    # Dimension weights
    weights: dict[str, float] = field(default_factory=lambda: {
        "clarity": 1.0,
        "specificity": 1.0,
        "structure": 0.8,
        "completeness": 1.2,
        "output_format": 0.8,
        "guardrails_system": 1.2,
        "guardrails_user": 0.6,
    })

    # Score labels
    score_labels: dict[str, int] = field(default_factory=lambda: {
        "excellent": 80,
        "good": 60,
        "fair": 40,
    })

    # Term lists
    vague_terms: tuple[str, ...] = (
        "good", "proper", "appropriate", "nice", "better", "best",
        "correct", "right", "wrong", "bad", "okay", "fine",
        "reasonable", "suitable", "adequate", "sufficient",
        "effective", "efficient", "optimal", "ideal",
    )

    output_format_markers: tuple[str, ...] = (
        "format", "respond", "output", "return", "provide", "give",
        "answer", "reply", "json", "markdown", "bullet", "list", "table",
    )

    guardrail_markers: tuple[str, ...] = (
        "never", "always", "must", "don't", "do not", "avoid", "refuse",
        "only", "cannot", "should not", "forbidden", "prohibited",
        "limit", "restrict", "boundary", "exception", "unless", "if not",
    )

    example_markers: tuple[str, ...] = (
        "example", "for instance", "such as", "e.g.", "like this",
    )

    role_markers: tuple[str, ...] = (
        "you are", "act as", "behave as", "role", "persona", "assistant", "expert",
    )

    context_markers: tuple[str, ...] = (
        "context", "background", "given", "assuming", "based on", "considering",
    )

    task_markers: tuple[str, ...] = (
        "task", "goal", "objective", "help", "assist", "create",
        "generate", "analyze", "review", "write",
    )

    flow_markers: tuple[str, ...] = (
        "first", "then", "next", "finally", "after", "before", "step",
    )

    scope_markers: tuple[str, ...] = (
        "only", "limited to", "focus on", "specifically", "exclusively",
    )

    edge_case_markers: tuple[str, ...] = (
        "if", "when", "unless", "except", "in case", "otherwise",
    )

    length_markers: tuple[str, ...] = (
        "brief", "concise", "detailed", "comprehensive",
        "short", "long", "words", "sentences", "paragraphs",
    )

    specific_formats: tuple[str, ...] = (
        "json", "xml", "yaml", "markdown", "html", "csv", "table",
    )

    @classmethod
    def from_yaml(cls, path: Path | str) -> "AnalysisConfig":
        """Load configuration from a YAML file.

        Args:
            path: Path to the YAML config file.

        Returns:
            AnalysisConfig instance with values from the file.

        Raises:
            FileNotFoundError: If the config file doesn't exist.
            yaml.YAMLError: If the file is invalid YAML.
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")

        with open(path) as f:
            data = yaml.safe_load(f) or {}

        return cls._from_dict(data)

    @classmethod
    def _from_dict(cls, data: dict[str, Any]) -> "AnalysisConfig":
        """Create config from a dictionary."""
        config = cls()

        # Load thresholds
        if "thresholds" in data:
            thresholds = data["thresholds"]
            if "min_word_count" in thresholds:
                config.min_word_count = thresholds["min_word_count"]
            if "max_sentence_length" in thresholds:
                config.max_sentence_length = thresholds["max_sentence_length"]

        # Load weights
        if "weights" in data:
            config.weights = {**config.weights, **data["weights"]}

        # Load score labels
        if "score_labels" in data:
            config.score_labels = {**config.score_labels, **data["score_labels"]}

        # Load term lists (convert lists to tuples)
        list_fields = [
            "vague_terms", "output_format_markers", "guardrail_markers",
            "example_markers", "role_markers", "context_markers",
            "task_markers", "flow_markers", "scope_markers",
            "edge_case_markers", "length_markers", "specific_formats",
        ]

        for field_name in list_fields:
            if field_name in data and isinstance(data[field_name], list):
                setattr(config, field_name, tuple(data[field_name]))

        return config

    def merge_with(self, override_path: Path | str) -> "AnalysisConfig":
        """Merge this config with overrides from another file.

        Values in the override file take precedence.

        Args:
            override_path: Path to the override YAML file.

        Returns:
            New AnalysisConfig with merged values.
        """
        override_path = Path(override_path)
        if not override_path.exists():
            raise FileNotFoundError(f"Override config not found: {override_path}")

        with open(override_path) as f:
            override_data = yaml.safe_load(f) or {}

        # Start with current config as dict
        merged = self._to_dict()

        # Deep merge override data
        _deep_merge(merged, override_data)

        return self._from_dict(merged)

    def _to_dict(self) -> dict[str, Any]:
        """Convert config to dictionary."""
        return {
            "thresholds": {
                "min_word_count": self.min_word_count,
                "max_sentence_length": self.max_sentence_length,
            },
            "weights": dict(self.weights),
            "score_labels": dict(self.score_labels),
            "vague_terms": list(self.vague_terms),
            "output_format_markers": list(self.output_format_markers),
            "guardrail_markers": list(self.guardrail_markers),
            "example_markers": list(self.example_markers),
            "role_markers": list(self.role_markers),
            "context_markers": list(self.context_markers),
            "task_markers": list(self.task_markers),
            "flow_markers": list(self.flow_markers),
            "scope_markers": list(self.scope_markers),
            "edge_case_markers": list(self.edge_case_markers),
            "length_markers": list(self.length_markers),
            "specific_formats": list(self.specific_formats),
        }

    def save_yaml(self, path: Path | str) -> None:
        """Save configuration to a YAML file.

        Args:
            path: Path to save the config file.
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w") as f:
            yaml.dump(self._to_dict(), f, default_flow_style=False, sort_keys=False)


def _deep_merge(base: dict, override: dict) -> None:
    """Deep merge override dict into base dict in place."""
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value


def load_config(path: Path | str | None = None) -> AnalysisConfig:
    """Load analysis configuration.

    Args:
        path: Optional path to a custom config file.
              If None, loads from default location.
              If default doesn't exist, returns built-in defaults.

    Returns:
        AnalysisConfig instance.
    """
    if path is not None:
        return AnalysisConfig.from_yaml(path)

    # Try to load default config
    if DEFAULT_CONFIG_PATH.exists():
        return AnalysisConfig.from_yaml(DEFAULT_CONFIG_PATH)

    # Fall back to built-in defaults
    return AnalysisConfig()


# Global config instance (can be replaced via load_config)
_current_config: AnalysisConfig | None = None


def get_config() -> AnalysisConfig:
    """Get the current analysis configuration.

    Loads default config on first call.
    """
    global _current_config
    if _current_config is None:
        _current_config = load_config()
    return _current_config


def set_config(config: AnalysisConfig) -> None:
    """Set the global analysis configuration."""
    global _current_config
    _current_config = config


def reset_config() -> None:
    """Reset to default configuration."""
    global _current_config
    _current_config = None
