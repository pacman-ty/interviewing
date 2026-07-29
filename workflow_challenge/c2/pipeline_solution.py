"""
Reference solution for the intake pipeline integration challenge --
the given code from pipeline.py with Tasks 1-4 integrated.

SPOILERS: attempt the tasks in pipeline.py before reading this.
A useful study move afterwards:  diff pipeline.py pipeline_solution.py

Verify with:  python pipeline_tests.py 4 pipeline_solution
"""

import copy


class PipelineError(Exception):
    """Any invalid pipeline definition or processing failure."""


def get_field(doc, name):
    """Read a field off a document; None if absent."""
    return doc.get("fields", {}).get(name)


class Context:
    """Mutable state carried through a single pipeline run."""

    def __init__(self, doc):
        self.doc = copy.deepcopy(doc)
        self.doc.setdefault("fields", {})
        self.errors = []
        self.tags = set()
        self.trace = []


# --------------------------- conditions (Task 2/3) ----------------------------

def evaluate_condition(cond, ctx):
    """Evaluate a condition dict against the current context.

    Forms (checked in this order):
        {"all": [conds]}   {"any": [conds]}   {"not": cond}
        {"has_tag": <label>}
        {"has_errors": true|false}
        {"field": <name>, "equals": <value>}
        {"field": <name>, "exists": true|false}   # exists == value is not None

    Lives outside any processor on purpose: the run loop uses it for step
    "when" clauses (Task 2) and routing reuses it verbatim (Task 3).
    """
    if not isinstance(cond, dict):
        raise PipelineError(f"condition must be a dict, got {cond!r}")
    if "all" in cond:
        return all(evaluate_condition(c, ctx) for c in cond["all"])
    if "any" in cond:
        return any(evaluate_condition(c, ctx) for c in cond["any"])
    if "not" in cond:
        return not evaluate_condition(cond["not"], ctx)
    if "has_tag" in cond:
        return cond["has_tag"] in ctx.tags
    if "has_errors" in cond:
        return bool(ctx.errors) == bool(cond["has_errors"])
    if "field" in cond:
        value = get_field(ctx.doc, cond["field"])
        if "equals" in cond:
            return value == cond["equals"]
        if "exists" in cond:
            return (value is not None) == bool(cond["exists"])
        raise PipelineError(f"field condition needs 'equals' or 'exists': {cond}")
    raise PipelineError(f"unrecognized condition: {cond}")


# ----------------------------- routing (Task 3) -------------------------------

def validate_routes(routes):
    for rule in routes:
        has_to = "to" in rule
        has_sub = "routes" in rule
        if has_to == has_sub:
            raise PipelineError(
                "each route rule needs exactly one of 'to' or 'routes'"
            )
        if has_sub:
            validate_routes(rule["routes"])


def resolve_route(routes, ctx):
    """First matching rule wins, depth-first. A rule with no "when" always
    matches. A nested group that matches but whose children all miss falls
    through to the next rule. Returns None if nothing matched."""
    for rule in routes:
        cond = rule.get("when")
        if cond is not None and not evaluate_condition(cond, ctx):
            continue
        if "to" in rule:
            return rule["to"]
        destination = resolve_route(rule["routes"], ctx)
        if destination is not None:
            return destination
    return None


# ------------------------------ processors ------------------------------------

PROCESSORS = {}


def register(cls):
    if not cls.kind:
        raise PipelineError(f"{cls.__name__} must declare a 'kind'")
    PROCESSORS[cls.kind] = cls()
    return cls


class Processor:
    """Base class for all processors."""

    kind = None

    def apply(self, ctx, config):
        raise NotImplementedError


@register
class SetField(Processor):
    kind = "set_field"

    def apply(self, ctx, config):
        ctx.doc["fields"][config["field"]] = config["value"]


@register
class NormalizeField(Processor):
    kind = "normalize"
    modes = {
        "upper": str.upper,
        "lower": str.lower,
        "title": str.title,
        "strip": str.strip,
    }

    def apply(self, ctx, config):
        field = config["field"]
        value = get_field(ctx.doc, field)
        if value is None:
            raise PipelineError(f"normalize: field '{field}' is missing")
        mode = config.get("mode", "strip")
        if mode not in self.modes:
            raise PipelineError(f"normalize: unknown mode '{mode}'")
        ctx.doc["fields"][field] = self.modes[mode](str(value))


@register
class RequireFields(Processor):
    kind = "require"

    def apply(self, ctx, config):
        for field in config["fields"]:
            value = get_field(ctx.doc, field)
            if value is None or value == "":
                ctx.errors.append(f"missing required field '{field}'")


@register
class AddTag(Processor):
    kind = "tag"

    def apply(self, ctx, config):
        ctx.tags.add(config["tag"])


@register
class DefaultField(Processor):
    """Task 1. Set a field only if it is missing or empty.

    config: {"kind": "default_field", "field": <name>, "value": <value>}
    """

    kind = "default_field"

    def apply(self, ctx, config):
        current = get_field(ctx.doc, config["field"])
        if current is None or current == "":
            ctx.doc["fields"][config["field"]] = config["value"]


@register
class RenameField(Processor):
    """Task 1. Move a value from one field name to another.

    config: {"kind": "rename_field", "from": <name>, "to": <name>}
    If the source field is absent, this is a no-op.
    """

    kind = "rename_field"

    def apply(self, ctx, config):
        fields = ctx.doc["fields"]
        if config["from"] in fields:
            fields[config["to"]] = fields.pop(config["from"])


# ------------------------------- pipeline -------------------------------------

_ON_ERROR_POLICIES = {"fail", "skip", "quarantine"}


class Pipeline:
    """An ordered list of steps applied to each incoming document, plus an
    optional routing table consulted after the steps finish (Task 3)."""

    def __init__(self, steps, routes=None):
        for step in steps:
            kind = step.get("kind")
            if kind not in PROCESSORS:
                raise PipelineError(f"unknown step kind '{kind}'")
            policy = step.get("on_error", "fail")
            if policy not in _ON_ERROR_POLICIES:
                raise PipelineError(f"unknown on_error policy '{policy}'")
        if routes is not None:
            validate_routes(routes)
        self.steps = steps
        self.routes = routes

    def run(self, doc):
        """Process one document. Returns a result dict; never mutates `doc`.

        The loop owns each step's lifecycle: it decides skipped vs ok vs
        error (Tasks 2 and 4) and records exactly one trace entry per step.
        Processors stay oblivious to conditions and error policy.
        """
        ctx = Context(doc)
        quarantined = False

        for step in self.steps:
            name = step.get("name", step["kind"])

            # Task 2: conditional execution.
            cond = step.get("when")
            if cond is not None and not evaluate_condition(cond, ctx):
                ctx.trace.append({"step": name, "status": "skipped"})
                continue

            try:
                PROCESSORS[step["kind"]].apply(ctx, step)
            except Exception as exc:
                # Task 4: per-step error policy (default "fail").
                policy = step.get("on_error", "fail")
                if policy == "fail":
                    raise
                ctx.trace.append(
                    {"step": name, "status": "error", "message": str(exc)}
                )
                if policy == "quarantine":
                    quarantined = True
                    break
                continue  # policy == "skip"

            ctx.trace.append({"step": name, "status": "ok"})

        result = self._result(ctx)

        # Task 4: quarantine bypasses routing entirely.
        if quarantined:
            result["destination"] = "quarantine"
        elif self.routes is not None:
            destination = resolve_route(self.routes, ctx)
            if destination is None:
                raise PipelineError("no route matched")
            result["destination"] = destination

        return result

    def _result(self, ctx):
        return {
            "doc": ctx.doc,
            "errors": list(ctx.errors),
            "tags": sorted(ctx.tags),
            "trace": list(ctx.trace),
        }
