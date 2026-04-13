from difflib import SequenceMatcher

from .nokia_interfaces import get_interface_descriptions
from .nokia_lag import get_lag_config, get_lag_state


def build_interface_index(device):
    """Build a unified searchable index of all ports and LAGs with resolved descriptions.

    For LAGs without a description, inherits descriptions from member port(s).
    Returns list of dicts with: id, type, description, admin_state, oper_state,
    speed, members (for LAGs), member_descriptions.
    """
    # Fetch port data
    ports = get_interface_descriptions(device)
    port_map = {p["port_id"]: p for p in ports}

    # Fetch LAG data
    lag_config = get_lag_config(device).get("lags", [])
    lag_state = get_lag_state(device).get("lags", [])
    lag_state_map = {l["lag_id"]: l for l in lag_state}

    index = []

    # Add physical ports
    for port in ports:
        index.append({
            "id": port["port_id"],
            "type": "port",
            "description": port["description"],
            "admin_state": port["admin_state"],
            "oper_state": port["oper_state"],
            "speed": port["speed"],
            "lag_member_of": port.get("lag_member_of", ""),
            "members": [],
            "member_descriptions": [],
        })

    # Add LAGs with resolved descriptions
    for lag in lag_config:
        lag_id = lag["lag_id"]
        state = lag_state_map.get(lag_id, {})
        description = lag["description"]

        # Collect member port descriptions
        member_descs = []
        for member_port_id in lag.get("member_ports", []):
            member = port_map.get(member_port_id, {})
            if member.get("description"):
                member_descs.append(f"{member_port_id}: {member['description']}")

        # If LAG has no description, derive from members
        if not description and member_descs:
            description = " / ".join(member_descs)

        index.append({
            "id": lag_id,
            "type": "lag",
            "description": description,
            "admin_state": lag.get("admin_state", ""),
            "oper_state": state.get("oper_state", ""),
            "speed": state.get("speed", ""),
            "lag_member_of": "",
            "members": lag.get("member_ports", []),
            "member_descriptions": member_descs,
            "active_members": state.get("active_members", 0),
            "total_members": state.get("total_members", 0),
        })

    return index


def search_interfaces(device, query, threshold=0.35, max_results=20):
    """Search ports and LAGs by description or ID.

    Returns matches sorted by relevance score. Supports:
    - Exact substring match on port/LAG ID (e.g. "1/1/1", "lag-1")
    - Fuzzy match on description
    - Match on LAG member port descriptions
    """
    index = build_interface_index(device)
    query_lower = query.lower().strip()
    if not query_lower:
        return index[:max_results]

    scored = []
    for entry in index:
        score = _score_entry(entry, query_lower)
        if score >= threshold:
            scored.append((score, entry))

    # Sort by score descending
    scored.sort(key=lambda x: x[0], reverse=True)
    return [entry for _, entry in scored[:max_results]]


def _score_entry(entry, query_lower):
    """Calculate relevance score for a single entry against a query."""
    best_score = 0.0
    entry_id = entry["id"].lower()
    description = entry["description"].lower()

    # Exact ID match
    if query_lower == entry_id:
        return 1.0

    # ID substring match
    if query_lower in entry_id:
        best_score = max(best_score, 0.9)

    # ID starts with query
    if entry_id.startswith(query_lower):
        best_score = max(best_score, 0.85)

    # Exact description substring match
    if query_lower in description:
        # Score higher for longer match proportion
        ratio = len(query_lower) / max(len(description), 1)
        best_score = max(best_score, 0.6 + ratio * 0.3)

    # Fuzzy match on description
    if description:
        ratio = SequenceMatcher(None, query_lower, description).ratio()
        best_score = max(best_score, ratio)

    # Check member descriptions for LAGs
    for md in entry.get("member_descriptions", []):
        md_lower = md.lower()
        if query_lower in md_lower:
            best_score = max(best_score, 0.7)
        else:
            ratio = SequenceMatcher(None, query_lower, md_lower).ratio()
            best_score = max(best_score, ratio * 0.8)

    return best_score
