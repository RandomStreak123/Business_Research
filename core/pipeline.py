"""
Middleware pipeline.

A Skill is one unit of work that reads from and writes to a shared
PipelineContext. A Pipeline is an ordered chain of Skills, run one
after another against the SAME context object — this is the
"middleware" pattern: each skill processes the context and hands it
forward, the way HTTP middleware passes a request/response object
through a chain of independent handlers, none of which know about
each other directly.

This decouples orchestration (what order things run in) from
implementation (what each step actually does) — adding, removing, or
reordering a skill never requires touching any other skill's code.
"""

from core.context import PipelineContext
from core.task_manager import TaskManager


class Skill:
    """Base class for one pipeline stage. Subclasses implement run()."""
    name: str = "skill"

    def run(self, context: PipelineContext) -> None:
        raise NotImplementedError


class Pipeline:
    def __init__(self, skills: list[Skill], tm: TaskManager):
        self.skills = skills
        self.tm = tm

    def run(self, context: PipelineContext) -> PipelineContext:
        for skill in self.skills:
            self.tm.log("middleware_dispatch", "pipeline", f"running skill: {skill.name}")
            skill.run(context)
        return context
