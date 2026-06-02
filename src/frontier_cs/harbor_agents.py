"""Custom Harbor agents used by the Frontier-CS wrapper."""

from __future__ import annotations

from pathlib import Path
import shutil

from harbor.agents.installed.codex import Codex


class CodexNoWebSearch(Codex):
    """Codex agent with the official top-level web search setting disabled."""

    def _build_register_mcp_servers_command(self) -> str | None:
        base = super()._build_register_mcp_servers_command()
        disable_web_search = (
            'cat >>"$CODEX_HOME/config.toml" <<\'TOML\'\n'
            'web_search = "disabled"\n'
            "TOML"
        )
        return f"{base}\n{disable_web_search}" if base else disable_web_search


class BBOPlaceCodexNoWebSearch(CodexNoWebSearch):
    """Codex agent installer compatible with BBOPlace's Ubuntu 18.04 image."""

    def _resolve_auth_json_path(self) -> Path | None:
        auth_path = super()._resolve_auth_json_path()
        if auth_path is not None:
            return auth_path
        if self._get_env("OPENAI_API_KEY"):
            return None
        default = Path.home() / ".codex" / "auth.json"
        return default if default.is_file() else None

    @staticmethod
    def _find_static_codex_binary() -> Path | None:
        candidates = [
            Path(
                "/home/ubuntu/.nvm/versions/node/v24.16.0/lib/node_modules/"
                "@openai/codex/node_modules/@openai/codex-linux-x64/vendor/"
                "x86_64-unknown-linux-musl/bin/codex"
            )
        ]
        for root in (Path.home() / ".nvm").glob(
            "versions/node/*/lib/node_modules/@openai/codex/node_modules/"
            "@openai/codex-linux-x64/vendor/x86_64-unknown-linux-musl/bin/codex"
        ):
            candidates.append(root)
        for candidate in candidates:
            if candidate.is_file():
                return candidate
        return None

    async def install(self, environment) -> None:
        """Install Codex via the host static binary instead of Node 22."""

        await self.exec_as_root(
            environment,
            command=(
                "if command -v apt-get &>/dev/null; then"
                "  apt-get update && apt-get install -y curl || true;"
                " fi;"
                " RG_PATH=$(command -v rg || true);"
                ' if [ -n "$RG_PATH" ] && [ "$RG_PATH" != "/usr/local/bin/rg" ]; then'
                '   ln -sf "$RG_PATH" /usr/local/bin/rg;'
                " fi"
            ),
            env={"DEBIAN_FRONTEND": "noninteractive"},
        )

        local_codex = self._find_static_codex_binary()
        if local_codex is None:
            fallback = shutil.which("codex")
            local_codex = Path(fallback) if fallback else None
        if local_codex is None or not local_codex.is_file():
            raise RuntimeError(
                "Could not find a local Codex static binary to upload into the "
                "BBOPlace container. Set up Codex on the host first."
            )

        await environment.upload_file(local_codex, "/usr/local/bin/codex")
        await self.exec_as_root(
            environment,
            command="chmod +x /usr/local/bin/codex && /usr/local/bin/codex --version",
        )
