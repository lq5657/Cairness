# Cairness Codex Adapter

Use the repository skill `$cc-harness` for every literal `cc-*` request.
Treat `.codex/runtime/core.yaml` and its referenced command manifests as the
runtime contract. Keep `.cairness/` as the shared project-state root.

`cc-start` is the high-level, read-only intent router. It is registered under
the runtime `scripts.start` entrypoint rather than `migrated_commands`, so it
does not have a lifecycle command manifest. Run it directly when the current
stage is unknown; it reports the legal next command and never executes it.

Do not claim completion without fresh deterministic verification evidence.
Do not implement business code without an in-progress change spec under
`.cairness/changes/`.
