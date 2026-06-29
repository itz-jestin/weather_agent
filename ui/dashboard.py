"""
ui/dashboard.py
Rich-powered terminal dashboard.
Shows live weather, markets, positions, and P&L.
"""

from __future__ import annotations

import time
from datetime import datetime

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

# force_terminal=True makes Rich work on Windows CMD / PowerShell
# highlight=False stops it re-colouring numbers unexpectedly
console = Console(force_terminal=True, highlight=False)


# ── Helper renderers ─────────────────────────────────────────────────────────

def weather_table(summaries: list[dict]) -> Table:
    t = Table(
        title="🌤  Live Weather – Tracked Cities",
        box=box.ROUNDED,
        border_style="cyan",
        show_lines=True,
    )
    t.add_column("City",        style="bold white",  width=14)
    t.add_column("Max °C",      justify="right",     width=8)
    t.add_column("Min °C",      justify="right",     width=8)
    t.add_column("Rain (mm)",   justify="right",     width=10)
    t.add_column("Wind (km/h)", justify="right",     width=12)
    t.add_column("Raining?",    justify="center",    width=10)

    for s in summaries:
        rain_icon = "🌧  YES" if s.get("will_rain") else "☀  NO"
        rain_color = "blue" if s.get("will_rain") else "yellow"
        t.add_row(
            s.get("city", "?"),
            str(s.get("max_temp_c", "?")),
            str(s.get("min_temp_c", "?")),
            str(round(s.get("total_precip_mm", 0), 2)),
            str(s.get("max_wind_kmh", "?")),
            Text(rain_icon, style=rain_color),
        )
    return t


def markets_table(markets: list[dict]) -> Table:
    t = Table(
        title="📊  Top Polymarket Weather Opportunities",
        box=box.ROUNDED,
        border_style="green",
        show_lines=False,
    )
    t.add_column("Question",     width=46)
    t.add_column("City",         width=12)
    t.add_column("Mkt Prob",     justify="right", width=9)
    t.add_column("Model Prob",   justify="right", width=11)
    t.add_column("Edge",         justify="right", width=8)
    t.add_column("Rec",          width=10)
    t.add_column("Vol $",        justify="right", width=9)

    for m in markets[:15]:
        edge = m.get("edge", 0)
        rec  = m.get("recommendation", "SKIP")
        edge_color = "green" if edge > 0 else "red" if edge < 0 else "white"
        rec_style  = {
            "BUY_YES": "bold green",
            "BUY_NO":  "bold red",
            "SKIP":    "dim",
        }.get(rec, "white")

        t.add_row(
            (m.get("question", "")[:44] + "…")
            if len(m.get("question", "")) > 44 else m.get("question", ""),
            str(m.get("matched_city") or "—"),
            f"{m.get('market_prob', 0):.1%}",
            f"{m.get('model_prob',  0):.1%}",
            Text(f"{edge:+.3f}", style=edge_color),
            Text(rec, style=rec_style),
            f"{m.get('volume', 0):,.0f}",
        )
    return t


def positions_table(positions: list[dict], history: list[dict]) -> Table:
    t = Table(
        title="💼  Paper Positions",
        box=box.ROUNDED,
        border_style="magenta",
        show_lines=True,
    )
    t.add_column("Question",   width=40)
    t.add_column("City",       width=12)
    t.add_column("Side",       width=6)
    t.add_column("Stake $",    justify="right", width=8)
    t.add_column("Kelly",      justify="right", width=7)
    t.add_column("Edge",       justify="right", width=7)
    t.add_column("Status",     width=9)

    for pos in positions:
        t.add_row(
            (pos.get("question", "")[:38] + "…")
            if len(pos.get("question", "")) > 38 else pos.get("question", ""),
            str(pos.get("city", "—")),
            Text(pos.get("side", "?"),
                 style="green" if pos["side"] == "YES" else "red"),
            f"${pos.get('stake_usd', 0):.2f}",
            f"{pos.get('kelly_frac', 0):.2%}",
            f"{pos.get('edge', 0):+.3f}",
            Text("OPEN", style="bold yellow"),
        )

    for h in history[-3:]:
        pnl   = h.get("pnl_usd", 0)
        color = "green" if pnl >= 0 else "red"
        t.add_row(
            (h.get("question", "")[:38] + "…")
            if len(h.get("question", "")) > 38 else h.get("question", ""),
            str(h.get("city", "—")),
            h.get("side", "?"),
            f"${h.get('stake_usd', 0):.2f}",
            f"{h.get('kelly_frac', 0):.2%}",
            f"{h.get('edge', 0):+.3f}",
            Text(f"{'WIN' if h.get('won') else 'LOSS'} {pnl:+.2f}", style=color),
        )
    return t


def stats_panel(stats: dict) -> Panel:
    roi_color = "green" if stats.get("roi_pct", 0) >= 0 else "red"
    lines = [
        f"[bold]Bankroll:[/bold]    [cyan]${stats.get('bankroll', 0):,.2f}[/cyan]",
        f"[bold]Starting:[/bold]    ${stats.get('starting', 0):,.2f}",
        f"[bold]ROI:[/bold]         [{roi_color}]{stats.get('roi_pct', 0):+.2f}%[/{roi_color}]",
        f"[bold]Total P&L:[/bold]   [{roi_color}]${stats.get('total_pnl', 0):+.2f}[/{roi_color}]",
        f"[bold]Total Staked:[/bold] ${stats.get('total_staked', 0):,.2f}",
        f"[bold]Open Positions:[/bold] {stats.get('open_positions', 0)}",
        f"[bold]Closed Trades:[/bold]  {stats.get('closed_trades', 0)}",
        f"[bold]Win Rate:[/bold]    {stats.get('win_rate', 0):.1f}%",
    ]
    return Panel(
        "\n".join(lines),
        title="📈  Portfolio Stats",
        border_style="yellow",
    )


# ── Snapshot display (non-live) ───────────────────────────────────────────────

def print_snapshot(
    weather:   list[dict],
    markets:   list[dict],
    positions: list[dict],
    history:   list[dict],
    stats:     dict,
    agent_log: str = "",
):
    console.rule(
        f"[bold blue]Weather Prediction Agent  |  {datetime.utcnow():%Y-%m-%d %H:%M UTC}",
        style="blue",
    )
    console.print()
    if weather:
        console.print(weather_table(weather))
    console.print()
    if markets:
        console.print(markets_table(markets))
    console.print()
    if positions or history:
        console.print(positions_table(positions, history))
    console.print()
    console.print(stats_panel(stats))
    if agent_log:
        console.print(Panel(agent_log, title="🤖  Agent Log", border_style="white"))
    console.rule(style="blue")
