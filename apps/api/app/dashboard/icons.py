"""Small local action symbols; visible labels always carry their meaning."""

from dash import html


def icon(name: str):
    return html.Span(className=f"ui-icon icon-{name}", **{"aria-hidden": "true"})
