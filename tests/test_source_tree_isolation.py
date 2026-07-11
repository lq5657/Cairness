"""Tests must never mutate framework assets in the repository source tree."""

import ast
from pathlib import Path
from typing import Optional, Set


REPO_ROOT = Path(__file__).resolve().parent.parent
MUTATING_METHODS = {
    "chmod",
    "mkdir",
    "rename",
    "rmdir",
    "touch",
    "unlink",
    "write_bytes",
    "write_text",
}
MUTATING_FUNCTIONS = {
    "os": {"chmod", "remove", "rename", "replace", "rmdir", "unlink"},
    "shutil": {"move", "rmtree"},
}


def _referenced_names(node: ast.AST) -> set[str]:
    return {child.id for child in ast.walk(node) if isinstance(child, ast.Name)}


def _scope_nodes(scope: ast.AST) -> list[ast.AST]:
    nodes: list[ast.AST] = []

    def visit(node: ast.AST) -> None:
        nodes.append(node)
        for child in ast.iter_child_nodes(node):
            if child is not scope and isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue
            visit(child)

    visit(scope)
    return nodes


def _source_tree_path_names(scope: ast.AST, inherited: Optional[Set[str]] = None) -> set[str]:
    assignments: list[tuple[str, ast.AST]] = []
    for node in _scope_nodes(scope):
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            value = node.value
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                if isinstance(target, ast.Name) and value is not None:
                    assignments.append((target.id, value))

    repository_roots = set(inherited or ())
    for name, value in assignments:
        if any(isinstance(child, ast.Name) and child.id == "__file__" for child in ast.walk(value)):
            repository_roots.add(name)

    source_tree_paths = set(inherited or ())
    changed = True
    while changed:
        changed = False
        for name, value in assignments:
            constants = {
                child.value
                for child in ast.walk(value)
                if isinstance(child, ast.Constant) and isinstance(child.value, str)
            }
            references = _referenced_names(value)
            derives_source_tree = "cairn-core" in constants and bool(references & repository_roots)
            if derives_source_tree or references & source_tree_paths:
                if name not in source_tree_paths:
                    source_tree_paths.add(name)
                    changed = True
    return source_tree_paths


def _scope_violations(
    scope: ast.AST,
    test_file: Path,
    inherited: Optional[Set[str]] = None,
) -> list[str]:
    violations: list[str] = []
    source_tree_names = _source_tree_path_names(scope, inherited)
    for node in _scope_nodes(scope):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        path_method_mutation = (
            node.func.attr in MUTATING_METHODS
            and bool(_referenced_names(node.func.value) & source_tree_names)
        )
        module_mutation = (
            isinstance(node.func.value, ast.Name)
            and node.func.attr in MUTATING_FUNCTIONS.get(node.func.value.id, set())
            and any(_referenced_names(argument) & source_tree_names for argument in node.args)
        )
        if path_method_mutation or module_mutation:
            violations.append(
                f"{test_file.relative_to(REPO_ROOT)}:{node.lineno} calls "
                f"{node.func.attr}() on a path derived from cairn-core"
            )
    return violations


def test_tests_do_not_mutate_cairn_core_source_tree():
    violations: list[str] = []
    for test_file in sorted((REPO_ROOT / "tests").glob("test_*.py")):
        if test_file == Path(__file__):
            continue
        tree = ast.parse(test_file.read_text(encoding="utf-8"), filename=str(test_file))
        module_source_tree_names = _source_tree_path_names(tree)
        violations.extend(_scope_violations(tree, test_file))
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                violations.extend(_scope_violations(node, test_file, module_source_tree_names))

    assert not violations, "\n".join(violations)
