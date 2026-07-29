"""
Document intake pipeline -- GIVEN CODE for the integration challenge.

This module already works. Read it, understand it, then extend it with the
tasks in PIPELINE_README.md. You will modify THIS file directly.

Before changing anything, run the regression suite -- it must pass now and
must STAY passing as you integrate each task:

    python pipeline_tests.py 0
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
        # Runs never mutate the caller's document.
        self.doc = copy.deepcopy(doc)
        self.doc.setdefault("fields", {})
        self.errors = []   # validation problems collected along the way
        self.tags = set()  # labels attached during processing
        self.trace = []    # audit log: one entry per step


# ------------------------------ processors ------------------------------------
#
# A processor is a small unit of work. Each subclass declares a `kind` (the
# name used in step configs) and implements apply(). The @register decorator
# adds an instance to the PROCESSORS registry, which Pipeline uses to look
# steps up by kind.

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
        """Do this processor's work. `config` is the raw step dict."""
        raise NotImplementedError


@register
class SetField(Processor):
    """Set a field to a fixed value.

    config: {"kind": "set_field", "field": <name>, "value": <value>}
    """

    kind = "set_field"

    def apply(self, ctx, config):
        ctx.doc["fields"][config["field"]] = config["value"]


@register
class NormalizeField(Processor):
    """Normalize a text field in place.

    config: {"kind": "normalize", "field": <name>, "mode": <mode>}
    modes: "upper", "lower", "title", "strip" (default "strip")
    Raises PipelineError if the field is missing.
    """

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
    """Record an error for every listed field that is missing or empty.

    config: {"kind": "require", "fields": [<name>, ...]}
    Does not stop the run -- errors accumulate on the context.
    """

    kind = "require"

    def apply(self, ctx, config):
        for field in config["fields"]:
            value = get_field(ctx.doc, field)
            if value is None or value == "":
                ctx.errors.append(f"missing required field '{field}'")


@register
class AddTag(Processor):
    """Attach a tag to the document.

    config: {"kind": "tag", "tag": <label>}
    """

    kind = "tag"

    def apply(self, ctx, config):
        ctx.tags.add(config["tag"])


# ------------------------------- pipeline -------------------------------------

class Pipeline:
    """An ordered list of steps applied to each incoming document.

    Each step is a dict with a "kind" naming a registered processor, plus
    whatever config that processor needs. An optional "name" overrides the
    label used in the trace.
    """

    def __init__(self, steps):
        for step in steps:
            kind = step.get("kind")
            if kind not in PROCESSORS:
                raise PipelineError(f"unknown step kind '{kind}'")
        self.steps = steps

    def run(self, doc):
        """Process one document. Returns a result dict; never mutates `doc`."""
        ctx = Context(doc)
        for step in self.steps:
            processor = PROCESSORS[step["kind"]]
            processor.apply(ctx, step)
            ctx.trace.append({"step": step.get("name", step["kind"]),
                              "status": "ok"})
        return self._result(ctx)

    def _result(self, ctx):
        return {
            "doc": ctx.doc,
            "errors": list(ctx.errors),
            "tags": sorted(ctx.tags),
            "trace": list(ctx.trace),
        }


if __name__ == "__main__":
    # Tiny demo: process one incoming referral.
    intake = Pipeline([
        {"kind": "normalize", "field": "patient_name", "mode": "title"},
        {"kind": "require", "fields": ["patient_name", "dob"]},
        {"kind": "tag", "tag": "intake"},
    ])
    result = intake.run({
        "id": "doc-1",
        "source": "fax",
        "fields": {"patient_name": "jane doe", "dob": "1990-04-02"},
    })
    for key in ("doc", "errors", "tags", "trace"):
        print(f"{key}: {result[key]}")
