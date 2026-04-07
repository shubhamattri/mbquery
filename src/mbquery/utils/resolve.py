"""Name-or-ID resolution for Metabase entities."""
from __future__ import annotations


def resolve_card_id(client, id_or_name: str) -> int:
    if id_or_name.isdigit():
        return int(id_or_name)
    cards = client.get("/api/card")
    matches = [c for c in cards if c["name"].lower() == id_or_name.lower()]
    if not matches:
        matches = [c for c in cards if id_or_name.lower() in c["name"].lower()]
    if len(matches) == 0:
        raise ValueError(f"No card found matching '{id_or_name}'")
    if len(matches) > 1:
        names = [f"  {m['id']}: {m['name']}" for m in matches[:5]]
        raise ValueError(f"Multiple cards match '{id_or_name}':\n" + "\n".join(names))
    return matches[0]["id"]
