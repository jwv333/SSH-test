"""Small shared UI helpers so pages don't repeat themselves."""

from __future__ import annotations

import streamlit as st

from utils.theme import STATUS


def theme_mode() -> str:
    """Best-effort light/dark detection for chart theming. Streamlit doesn't
    expose the viewer's resolved theme reliably, so this defaults to light,
    which is also this app's configured default in .streamlit/config.toml."""
    try:
        base = st.get_option("theme.base")
        if base in ("light", "dark"):
            return base
    except Exception:
        pass
    return "light"


def page_header(title: str, subtitle: str = "") -> None:
    st.title(title)
    if subtitle:
        st.caption(subtitle)


def sample_banner(is_live: bool, detail: str = "") -> None:
    if is_live:
        return
    msg = "📊 Showing **sample data** -- BigQuery isn't connected yet, or this table hasn't synced."
    if detail:
        msg += f" {detail}"
    st.info(msg, icon="📊")


def money(x) -> str:
    try:
        return f"${x:,.0f}"
    except (TypeError, ValueError):
        return "--"


def money2(x) -> str:
    try:
        return f"${x:,.2f}"
    except (TypeError, ValueError):
        return "--"


def pct(x) -> str:
    try:
        return f"{x * 100:.1f}%"
    except (TypeError, ValueError):
        return "--"


def status_badge(severity: str) -> str:
    """A small colored-dot + label prefix for an insight card, per the dataviz
    skill's rule that status colors ship with an icon/label, never color alone."""
    icons = {"good": "✅", "warning": "⚠️", "serious": "🟠", "critical": "🔴", "info": "ℹ️"}
    labels = {"good": "Good", "warning": "Watch", "serious": "Attention", "critical": "Critical", "info": "Note"}
    icon = icons.get(severity, "ℹ️")
    label = labels.get(severity, "Note")
    color = STATUS.get(severity, "#898781")
    return f'<span style="color:{color}; font-weight:600;">{icon} {label}</span>'
