"""Pure read-only validation. Never writes artifacts or awards approval."""


def schema_errors(value, schema, path="$", depth=0):
    errors = []
    if depth > 64:
        return [f"{path}: nesting limit exceeded"]
    kind = schema.get("type")
    valid = {
        "object": isinstance(value, dict), "array": isinstance(value, list),
        "string": isinstance(value, str), "boolean": type(value) is bool,
        "integer": type(value) is int,
    }
    if kind and not valid.get(kind, False):
        return [f"{path}: expected {kind}"]
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: not in allowed values")
    if isinstance(value, dict):
        props = schema.get("properties", {})
        for key in schema.get("required", []):
            if key not in value:
                errors.append(f"{path}.{key}: required")
        if schema.get("additionalProperties") is False:
            for key in value.keys() - props.keys():
                errors.append(f"{path}.{key}: unexpected field")
        for key in value.keys() & props.keys():
            errors.extend(schema_errors(value[key], props[key], f"{path}.{key}", depth+1))
    elif isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            errors.append(f"{path}: too few items")
        for i, item in enumerate(value):
            errors.extend(schema_errors(item, schema.get("items", {}), f"{path}[{i}]", depth+1))
    elif isinstance(value, str):
        if len(value.strip()) < schema.get("minLength", 0):
            errors.append(f"{path}: empty text")
        if "REPLACE_ME" in value or value.strip().lower() in {"todo", "tbd"}:
            errors.append(f"{path}: unresolved placeholder")
    elif type(value) is int:
        if value < schema.get("minimum", value) or value > schema.get("maximum", value):
            errors.append(f"{path}: out of range")
    return errors


def unique(items, label, errors):
    if len(set(items)) != len(items):
        errors.append(f"{label}: duplicate IDs")


def validate(stage, data, schema, rules, brief, upstream):
    errors = schema_errors(data, schema)
    if errors:
        return errors
    if stage == "brief":
        unique(data["screen_ids"], "screen_ids", errors)
        unique([r["id"] for r in data["references"]], "references", errors)
    elif stage == "research":
        refs = {r["id"]: r for r in brief["references"]}
        unique([r["id"] for r in data["references"]], "references", errors)
        for ref in data["references"]:
            source = refs.get(ref["id"])
            if not source or ref["evidence"] not in source["excerpt"]:
                errors.append(f"reference {ref['id']}: evidence must quote the supplied excerpt")
    elif stage == "plan":
        ids = [s["id"] for s in data["screens"]]
        unique(ids, "screens", errors)
        if set(ids) != set(brief["screen_ids"]):
            errors.append("screens: must cover exactly the requested screen IDs")
        unique([f["id"] for f in data["flows"]], "flows", errors)
        covered = set()
        for flow in data["flows"]:
            covered.update(flow["screen_ids"])
            if not set(flow["screen_ids"]) <= set(ids):
                errors.append(f"flow {flow['id']}: unknown screen")
        if set(ids) - covered:
            errors.append("flows: every requested screen must appear in a flow")
    elif stage == "concept":
        frames = data["frames"]
        limits = rules["frame"]
        if not limits["min_count"] <= len(frames) <= limits["max_count"]:
            errors.append("frames: expected 2–3 key screens")
        unique([f["id"] for f in frames], "frames", errors)
        unique([f["screen_id"] for f in frames], "key screens", errors)
        for frame in frames:
            if frame["screen_id"] not in brief["screen_ids"]:
                errors.append(f"frame {frame['id']}: unknown screen")
            if any(frame[k] != limits[k] for k in ("width", "height")):
                errors.append(f"frame {frame['id']}: must be 390×844")
    elif stage == "design":
        if data["tokens"] != rules["tokens"]:
            errors.append("tokens: must match rules.json exactly; no invented tokens or values")
        components = data["components"]
        ids = [c["id"] for c in components]
        unique(ids, "components", errors)
        for c in components:
            for field, prefix in (("fill", "colors."), ("text_color", "colors."),
                                  ("radius", "rounded."), ("typography", "typography."),
                                  ("spacing", "spacing.")):
                if c[field] not in rules["tokens"] or not c[field].startswith(prefix):
                    errors.append(f"component {c['id']}: invalid {field} token")
            if c["shadow"]:
                errors.append(f"component {c['id']}: shadows are forbidden")
            if c["kind"] in rules["interactive_kinds"] and c["radius"] != "rounded.full":
                errors.append(f"component {c['id']}: interactive shape must be a pill")
            if c["kind"] == "input" and c["radius"] != "rounded.sm":
                errors.append(f"component {c['id']}: input radius must be rounded.sm")
            accent = "colors.accent" in (c["fill"], c["text_color"])
            if accent and (c["kind"] not in {"badge", "text"} or c["accent_usage"] == "none"):
                errors.append(f"component {c['id']}: blue is only for commercial badges/callouts")
            if c["variant"] == "primary" and (c["kind"] != "button" or
                    c["fill"] != "colors.primary" or c["text_color"] != "colors.on-primary"):
                errors.append(f"component {c['id']}: primary CTA must be ink with white text")
            if c["variant"] == "featured_pricing" and (c["kind"] != "card" or c["fill"] != "colors.canvas-soft"):
                errors.append(f"component {c['id']}: featured pricing must use soft canvas")
        screen_ids = [s["id"] for s in data["screens"]]
        unique(screen_ids, "screens", errors)
        if set(screen_ids) != set(brief["screen_ids"]):
            errors.append("screens: final design must cover all requested screens")
        by_id = {c["id"]: c for c in components}
        for screen in data["screens"]:
            if any(screen[k] != rules["frame"][k] for k in ("width", "height")):
                errors.append(f"screen {screen['id']}: must be 390×844")
            if not set(screen["component_ids"]) <= set(ids):
                errors.append(f"screen {screen['id']}: unknown component")
            accent_count = sum(1 for cid in screen["component_ids"] if cid in by_id and
                               "colors.accent" in (by_id[cid]["fill"], by_id[cid]["text_color"]))
            if accent_count > 2:
                errors.append(f"screen {screen['id']}: at most two blue elements")
    elif stage == "review":
        check_ids = [c["id"] for c in data["checks"]]
        unique(check_ids, "review checks", errors)
        if set(check_ids) != set(rules["review_checks"]):
            errors.append("review: all required checks must be present")
        for check in data["checks"]:
            if check["status"] != "pass":
                errors.append(f"review {check['id']}: {check['status']} — {check['evidence']}")
        for finding in data["findings"]:
            errors.append(f"return_to={finding['return_to']}: {finding['message']}")
    if stage in {"plan", "design"} and data["asset_policy"] != rules["policy"]:
        errors.append("service invariant: private by default; owner choice and seller review required")
    return errors
