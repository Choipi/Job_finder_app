"""ATS adapters."""

from __future__ import annotations

from . import ashby, greenhouse, lever, smartrecruiters, workable

ADAPTERS = {
    module.NAME: module
    for module in (ashby, greenhouse, lever, smartrecruiters, workable)
}


def get_adapter(name: str):
    return ADAPTERS.get(name)
