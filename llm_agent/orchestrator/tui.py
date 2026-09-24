"""Komunikat końcowy do TUI (rich): użyty model, uzasadnienie, job_id, status, ścieżka; przy porażce — co próbowano."""
from __future__ import annotations

from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .summary import FinalSummary


def render_final(summary: FinalSummary, console: Console | None = None) -> None:
    console = console or Console()
    ok = summary.status == "SUCCESS"
    grid = Table.grid(padding=(0, 2))
    grid.add_column(style="bold")
    grid.add_column()
    if summary.user_dir:
        grid.add_row("Pliki (WCSS)", summary.user_dir)
    if ok:
        grid.add_row("Model", f"{summary.model} ({summary.agent})")
        grid.add_row("Uzasadnienie", summary.rationale or "-")
        grid.add_row("job_id", str(summary.job_id or "-"))
        grid.add_row("Status", Text("SUCCESS", style="bold green"))
        grid.add_row("Wynik", summary.output_path or "-")
    else:
        grid.add_row("Status", Text("FAILED", style="bold red"))
        grid.add_row("Powód", summary.error_message or summary.error_code or "-")
        if summary.rationale:
            grid.add_row("Kontekst", summary.rationale)

    parts: list = [grid]
    if summary.attempts:
        t = Table(title="Próby", show_lines=False)
        for col in ("#", "Agent", "Status", "Typ błędu", "job_id", "Szczegóły"):
            t.add_column(col)
        for i, a in enumerate(summary.attempts, 1):
            t.add_row(str(i), a.agent, a.status, a.failure_type or "-", a.job_id or "-", (a.details or "")[:80])
        parts.append(t)
    for w in summary.warnings:
        parts.append(Text(f"Uwaga: {w}", style="yellow"))
    console.print(Panel(Group(*parts), title="Orkiestrator audio", border_style="green" if ok else "red"))
