"""Command-line interface for pi-rpc."""

from __future__ import annotations

from cyclopts import App

from pi_rpc.cli_commands import jobs, lifecycle, prompting, session_controls, visibility
from pi_rpc.cli_support.extension_ui import (
    build_ui_response_request as _build_ui_response_request,
)
from pi_rpc.cli_support.extension_ui import (
    extension_ui_request_to_response as _extension_ui_request_to_response,
)
from pi_rpc.cli_support.extension_ui import (
    maybe_interactive_extension_ui_response as _maybe_interactive_extension_ui_response,
)
from pi_rpc.cli_support.extension_ui import (
    parse_confirmed as _parse_confirmed,
)
from pi_rpc.cli_support.extension_ui import (
    print_extension_ui_request as _print_extension_ui_request,
)
from pi_rpc.cli_support.model_resolution import (
    extract_model_refs as _extract_model_refs,
)
from pi_rpc.cli_support.model_resolution import (
    model_ref as _model_ref,
)
from pi_rpc.cli_support.model_resolution import (
    resolve_model_for_session as _resolve_model_for_session,
)
from pi_rpc.cli_support.model_resolution import (
    resolve_model_from_available_models as _resolve_model_from_available_models,
)
from pi_rpc.cli_support.payloads import (
    build_bash_request as _build_bash_request,
)
from pi_rpc.cli_support.payloads import (
    build_image_payloads as _build_image_payloads,
)
from pi_rpc.cli_support.payloads import (
    build_message_request as _build_message_request,
)
from pi_rpc.cli_support.payloads import (
    build_prompt_request as _build_prompt_request,
)
from pi_rpc.cli_support.runners import (
    run_abort_bash_command as _run_abort_bash_command,
)
from pi_rpc.cli_support.runners import (
    run_bash_command as _run_bash_command,
)
from pi_rpc.cli_support.runners import (
    run_command_and_print as _run_command_and_print,
)
from pi_rpc.cli_support.runners import (
    run_control_command as _run_control_command,
)
from pi_rpc.cli_support.runners import (
    run_control_request as _run_control_request,
)
from pi_rpc.cli_support.runners import (
    run_prompt as _run_prompt,
)
from pi_rpc.cli_support.runners import (
    run_read_only_command as _run_read_only_command,
)
from pi_rpc.cli_support.runners import (
    run_ui_response_command as _run_ui_response_command,
)
from pi_rpc.cli_support.summaries import (
    print_abort_bash_summary as _print_abort_bash_summary,
)
from pi_rpc.cli_support.summaries import (
    print_bash_summary as _print_bash_summary,
)

__all__ = [
    "_build_bash_request",
    "_build_image_payloads",
    "_build_message_request",
    "_build_prompt_request",
    "_build_ui_response_request",
    "_extension_ui_request_to_response",
    "_extract_model_refs",
    "_maybe_interactive_extension_ui_response",
    "_model_ref",
    "_parse_confirmed",
    "_print_abort_bash_summary",
    "_print_bash_summary",
    "_print_extension_ui_request",
    "_resolve_model_for_session",
    "_resolve_model_from_available_models",
    "_run_abort_bash_command",
    "_run_bash_command",
    "_run_command_and_print",
    "_run_control_command",
    "_run_control_request",
    "_run_prompt",
    "_run_read_only_command",
    "_run_ui_response_command",
    "app",
    "main",
]

app = App(help="Remote control for long-running Pi RPC sessions.")

lifecycle.register(app)
prompting.register(app)
session_controls.register(app)
visibility.register(app)
jobs.register(app)


def main() -> None:
    """Run the pi-rpc command-line application."""

    app()
