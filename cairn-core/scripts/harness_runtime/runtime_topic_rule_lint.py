"""Pure topic-rule shape checks used by ``cc-lint``."""

from __future__ import annotations

from collections.abc import Mapping


TOPIC_RULE_MARKERS = (
    "#### Skill Anatomy",
    "**When To Use**",
    "**When Not To Use**",
    "**Process**",
    "**Common Rationalizations**",
    "**Red Flags**",
    "**Verification**",
)
TOPIC_RULE_YAML_REQUIRED_KEYS = (
    "id", "description", "trigger", "skip", "process", "anti_rationalization", "red_flags", "checks"
)
TOPIC_RULE_RATIONALIZATION_HEADER = "| Rationalization | Why It Is Invalid | Required Response |"
TOPIC_RULE_REQUIRED_MARKERS = TOPIC_RULE_MARKERS


def validate_topic_rule_yaml(topic_key: str, data: Mapping[str, object]) -> list[str]:
    errors = [
        f"topic rule {topic_key} missing required key {key}"
        for key in TOPIC_RULE_YAML_REQUIRED_KEYS
        if key not in data
    ]
    anti_rationalization = data.get("anti_rationalization")
    if isinstance(anti_rationalization, list):
        for index, entry in enumerate(anti_rationalization):
            if isinstance(entry, dict) and ("claim" not in entry or "reality" not in entry):
                errors.append(
                    f"topic rule {topic_key} anti_rationalization[{index}] missing claim/reality"
                )
    return errors


def validate_topic_rule_markdown(topic_key: str, text: str) -> list[str]:
    errors: list[str] = []
    if not text.startswith("---\n"):
        errors.append(f"topic rule {topic_key} missing YAML frontmatter")
    for key in ("alwaysApply:", "description:"):
        if key not in text:
            errors.append(f"topic rule {topic_key} missing frontmatter key {key.rstrip(':')}")
    previous_position = -1
    for marker in TOPIC_RULE_MARKERS:
        position = text.find(marker)
        if position == -1:
            errors.append(f"topic rule {topic_key} missing skill-like section {marker}")
            continue
        if position < previous_position:
            errors.append(f"topic rule {topic_key} has section out of order {marker}")
        previous_position = position
    if TOPIC_RULE_RATIONALIZATION_HEADER not in text:
        errors.append(f"topic rule {topic_key} missing anti-rationalization table")
    return errors
