"""Review document verification checks used by cc-verify."""

from __future__ import annotations

from pathlib import Path

from change_docs import named_table_rows, parse_findings


def find_section_marker(lines: list[str], marker: str) -> int:
    """Find the line index of a cc-verify-key marker."""
    for index, line in enumerate(lines):
        if marker in line:
            return index
    return -1


def check_review_coverage(project_root: Path, change_id: str) -> dict[str, object]:
    """Check that review.md has a complete file_review_scope table."""
    review_path = project_root / ".cairness" / "changes" / change_id / "review.md"
    log_path = project_root / ".cairness" / "changes" / change_id / "log.md"

    if not review_path.exists():
        return {
            "name": "review-coverage",
            "kind": "harness",
            "command": [],
            "cwd": str(project_root),
            "status": "failed",
            "exit_code": 1,
            "duration_ms": 0,
            "stdout": "",
            "stderr": f"{review_path} not found",
            "fingerprints": [f"{review_path} not found"],
            "warnings": [],
        }

    lines = review_path.read_text(encoding="utf-8").splitlines()
    marker_idx = find_section_marker(lines, "cc-verify-key: file_review_scope")
    if marker_idx < 0:
        return {
            "name": "review-coverage",
            "kind": "harness",
            "command": [],
            "cwd": str(project_root),
            "status": "failed",
            "exit_code": 1,
            "duration_ms": 0,
            "stdout": "",
            "stderr": "file_review_scope section not found in review.md",
            "fingerprints": ["file_review_scope missing"],
            "warnings": [],
        }

    table_start = marker_idx + 1
    while table_start < len(lines) and (
        not lines[table_start].strip()
        or lines[table_start].strip().startswith("<!--")
    ):
        table_start += 1
    rows = named_table_rows(lines, table_start)
    if not rows:
        return {
            "name": "review-coverage",
            "kind": "harness",
            "command": [],
            "cwd": str(project_root),
            "status": "failed",
            "exit_code": 1,
            "duration_ms": 0,
            "stdout": "",
            "stderr": "file_review_scope table is empty or unparseable",
            "fingerprints": ["file_review_scope empty"],
            "warnings": [],
        }

    errors: list[str] = []
    warnings_list: list[str] = []
    for row in rows:
        status = row.get("Review Status", row.get("review_status", ""))
        notes = row.get("Notes", row.get("notes", ""))
        filename = row.get("File", row.get("file", "unknown"))

        if status == "not_reviewed" and not notes:
            errors.append(f"{filename}: not_reviewed but no notes explaining why")

        if status == "out_of_scope_flagged" and log_path.exists():
            log_content = log_path.read_text(encoding="utf-8")
            if "spec_review_flag" not in log_content:
                warnings_list.append(
                    f"{filename}: out_of_scope_flagged but no spec_review_flag found in log.md"
                )

    status = "failed" if errors else "passed"
    return {
        "name": "review-coverage",
        "kind": "harness",
        "command": [],
        "cwd": str(project_root),
        "status": status,
        "exit_code": 1 if errors else 0,
        "duration_ms": 0,
        "stdout": f"files in scope: {len(rows)}" if not errors else "",
        "stderr": "\n".join(errors + warnings_list),
        "fingerprints": errors + warnings_list,
        "warnings": warnings_list,
    }


def check_finding_locations(project_root: Path, change_id: str) -> dict[str, object]:
    """Check that finding existing_code matches actual file content."""
    review_path = project_root / ".cairness" / "changes" / change_id / "review.md"

    if not review_path.exists():
        return {
            "name": "finding-locations",
            "kind": "harness",
            "command": [],
            "cwd": str(project_root),
            "status": "failed",
            "exit_code": 1,
            "duration_ms": 0,
            "stdout": "",
            "stderr": f"{review_path} not found",
            "fingerprints": [f"{review_path} not found"],
            "warnings": [],
        }

    content = "\n".join(review_path.read_text(encoding="utf-8").splitlines())
    mismatches: list[str] = []
    matched = 0
    no_existing_code = 0
    important_with_location_no_code: list[str] = []

    for detail in parse_findings(content):
        if not detail.location:
            continue
        parts = detail.location.rsplit(":", 1)
        if len(parts) != 2:
            continue
        file_path = parts[0]
        finding_level = detail.level or "unknown"
        code = detail.existing_code

        if not code.strip():
            no_existing_code += 1
            if finding_level in ("Critical", "Important"):
                important_with_location_no_code.append(
                    f"{file_path} ({finding_level}): has Location but no Existing Code"
                )
            continue

        normalized_code = "\n".join(
            line.strip() for line in code.strip().splitlines() if line.strip()
        )
        target_path = project_root / file_path
        if not target_path.exists():
            mismatches.append(f"{file_path}: target file not found")
            continue

        file_content = target_path.read_text(encoding="utf-8")
        if code.strip() in file_content:
            matched += 1
        elif normalized_code and normalized_code in "\n".join(
            line.strip() for line in file_content.splitlines()
        ):
            matched += 1
        else:
            meaningful_lines = [
                line
                for line in code.strip().splitlines()
                if line.strip() and not line.strip().startswith("//")
            ]
            if meaningful_lines and meaningful_lines[0].strip() in file_content:
                matched += 1
            else:
                first_line = code.strip().split("\n")[0].strip() if code.strip() else ""
                mismatches.append(
                    f"{file_path}:{parts[1]} — existing_code not found in file "
                    f"(first line: {first_line[:80]})"
                )

    status = "failed" if mismatches else "passed"
    stderr_lines = list(mismatches)
    if important_with_location_no_code:
        stderr_lines.append(
            "Important/Critical findings with Location but no Existing Code: "
            f"{len(important_with_location_no_code)}"
        )
        stderr_lines.extend(f"  - {item}" for item in important_with_location_no_code)
    return {
        "name": "finding-locations",
        "kind": "harness",
        "command": [],
        "cwd": str(project_root),
        "status": status,
        "exit_code": 1 if mismatches else 0,
        "duration_ms": 0,
        "stdout": (
            "locations checked: "
            f"{matched + len(mismatches) + no_existing_code} "
            f"(matched: {matched}, no existing_code: {no_existing_code})"
        ),
        "stderr": "\n".join(stderr_lines),
        "fingerprints": mismatches
        + [
            f"no_existing_code:{item.split(':')[0]}"
            for item in important_with_location_no_code
        ],
        "warnings": [
            f"Important/Critical finding lacking Existing Code: {item}"
            for item in important_with_location_no_code
        ],
    }


def check_risk_triage(project_root: Path, change_id: str) -> dict[str, object]:
    """Check that if risk_triage marker exists, the table is populated."""
    review_path = project_root / ".cairness" / "changes" / change_id / "review.md"

    if not review_path.exists():
        return {
            "name": "risk-triage",
            "kind": "harness",
            "command": [],
            "cwd": str(project_root),
            "status": "skipped",
            "exit_code": 0,
            "duration_ms": 0,
            "stdout": "",
            "stderr": f"{review_path} not found",
            "fingerprints": [],
            "warnings": [],
        }

    lines = review_path.read_text(encoding="utf-8").splitlines()
    marker_idx = find_section_marker(lines, "cc-verify-key: risk_triage")
    if marker_idx < 0:
        return {
            "name": "risk-triage",
            "kind": "harness",
            "command": [],
            "cwd": str(project_root),
            "status": "passed",
            "exit_code": 0,
            "duration_ms": 0,
            "stdout": "risk_triage not present (change below threshold or Agent chose to skip)",
            "stderr": "",
            "fingerprints": [],
            "warnings": [],
        }

    table_start = marker_idx + 1
    while table_start < len(lines) and (
        not lines[table_start].strip()
        or lines[table_start].strip().startswith("<!--")
    ):
        table_start += 1
    rows = named_table_rows(lines, table_start)
    if not rows:
        return {
            "name": "risk-triage",
            "kind": "harness",
            "command": [],
            "cwd": str(project_root),
            "status": "failed",
            "exit_code": 1,
            "duration_ms": 0,
            "stdout": "",
            "stderr": (
                "risk_triage marker present but table is empty — "
                "risk_triage was indicated but not completed"
            ),
            "fingerprints": ["risk_triage table empty"],
            "warnings": [],
        }

    return {
        "name": "risk-triage",
        "kind": "harness",
        "command": [],
        "cwd": str(project_root),
        "status": "passed",
        "exit_code": 0,
        "duration_ms": 0,
        "stdout": f"risk_triage populated with {len(rows)} risk area(s)",
        "stderr": "",
        "fingerprints": [],
        "warnings": [],
    }
