# Cairness Codex Adapter

Use the repository skill `$cc-harness` for every literal `cc-*` request.
Treat `.codex/runtime/core.yaml` and its referenced command manifests as the
runtime contract. Keep `.cairness/` as the shared project-state root.

For this Codex adapter, execute every literal `cc-*` command through
`.codex/scripts/<command>`. Never substitute a `.claude/scripts/*` path, even
when a Claude Code adapter is installed in the same project. In particular,
the stage probe is:

```text
.codex/scripts/cc-start --intent status
```

Some shared manifests retain `.claude/...` as a logical compatibility path.
That spelling is resolved to the active framework internally; it is not a
literal shell path to execute. When a manifest names a script for Codex, use
the physical `.codex/scripts/...` path.

`cc-start` is the high-level, read-only intent router. It is registered under
the runtime `scripts.start` entrypoint rather than `migrated_commands`, so it
does not have a lifecycle command manifest. Run it directly when the current
stage is unknown; it reports the legal next command and never executes it.

Do not claim completion without fresh deterministic verification evidence.
Do not implement business code without an in-progress change spec under
`.cairness/changes/`.
