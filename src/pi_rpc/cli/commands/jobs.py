"""Detached job inspection commands."""

from __future__ import annotations

import sys

from cyclopts import App

from pi_rpc.cli.support.common import print_json
from pi_rpc.jobs.manager import job_text, list_job_records, read_job_frames, read_job_record
from pi_rpc.models import OutputFormat


def register(app: App) -> None:
    """Register detached job commands."""

    @app.command
    def jobs(*, output: OutputFormat = "human") -> None:
        """List detached pi-rpc jobs."""

        records = list_job_records()
        if output == "json":
            print_json({"jobs": [record.as_dict() for record in records]})
            return

        if not records:
            print("No detached pi-rpc jobs are known yet.")
            return

        print("Jobs:")
        for record in records:
            session = record.session_id or "-"
            print(f"- {record.job_id}  {record.kind}  {record.status}  session={session}")

    @app.command(name="job-status")
    def job_status(job_id: str, *, output: OutputFormat = "human") -> None:
        """Show detached job metadata."""

        try:
            record = read_job_record(job_id)
        except (OSError, ValueError) as exc:
            print(f"Job not found: {job_id}", file=sys.stderr)
            raise SystemExit(1) from exc

        if output == "json":
            print_json(record.as_dict())
            return

        print(f"Job:      {record.job_id}")
        print(f"Kind:     {record.kind}")
        print(f"Status:   {record.status}")
        print(f"PID:      {record.pid}")
        print(f"Session:  {record.session_id or '-'}")
        print(f"Created:  {record.created_at}")
        print(f"Updated:  {record.updated_at}")
        print(f"Frames:   {record.frames_path}")
        print(f"Log:      {record.log_path}")
        if record.error:
            print(f"Error:    {record.error}")

    @app.command(name="job-result")
    def job_result(job_id: str, *, output: OutputFormat = "human") -> None:
        """Show detached job result frames or final assistant text."""

        try:
            record = read_job_record(job_id)
            frames = read_job_frames(job_id)
        except (OSError, ValueError) as exc:
            print(f"Job not found: {job_id}", file=sys.stderr)
            raise SystemExit(1) from exc

        if output == "json":
            print_json({"job": record.as_dict(), "frames": frames})
            return

        text = job_text(frames)
        if text:
            print(text)
            return
        if record.error:
            print(f"Job failed: {record.error}", file=sys.stderr)
            raise SystemExit(1)
        print(f"No assistant text captured for job {job_id} ({record.status}).")
