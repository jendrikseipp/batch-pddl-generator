#! /usr/bin/env python3

"""Parse input task into PDDL model and compute hash representation for it."""

import io
import hashlib
import os
from pathlib import Path
import sys

DIR = Path(__file__).resolve().parent
REPO = DIR.parent

try:
    DOWNWARD_DIR = Path(os.environ["DOWNWARD_REPO"])
except KeyError:
    sys.exit("Error: the DOWNWARD_REPO environment variable must point to a Fast Downward repo.")
TRANSLATOR_DIR = DOWNWARD_DIR / "src"

sys.path.insert(0, str(TRANSLATOR_DIR))

from translate.pddl_parser import pddl_file
import translate.options as options


def dump_task(task):
    temp_out = io.StringIO()
    sys.stdout = temp_out

    # print(f"Domain: {task.domain_name}")
    # print(f"Task: {task.task_name}")
    # print(f"Requirements: {sorted(task.requirements.requirements)}")
    # print(f"Types: {sorted(repr(typ) for typ in task.types)}")
    print(f"Objects: {sorted(str(obj) for obj in task.objects)}")
    print("Predicates:")
    for pred in task.predicates:
        print(f"  {pred}")
    print("Functions:")
    for func in sorted(str(f) for f in task.functions):
        print(f"  {func}")
    print("Init:")
    for fact in sorted(str(f) for f in task.init):
        print(f"  {fact}")
    print("Goal:")
    # TODO: sort conditions in actions, axioms and goals.
    task.goal.dump()
    print("Actions:")
    for action in sorted(task.actions, key=lambda a: a.name):
        action.dump()
    if task.axioms:
        print("Axioms:")
        for axiom in sorted(task.axioms, key=lambda a: a.name):
            axiom.dump()

    sys.stdout = sys.__stdout__

    return temp_out.getvalue()


def main():
    if len(sys.argv) != 3:
        print("Usage: python hash-instance.py <domain.pddl> <problem.pddl>", file=sys.stderr)
        sys.exit(1)
    
    domain_file = sys.argv[1]
    problem_file = sys.argv[2]
    
    options.set_options([domain_file, problem_file])
    task = pddl_file.open()
    task_string = dump_task(task)
    debug = False
    if debug:
        print(task_string)
    m = hashlib.md5()
    m.update(task_string.encode("utf-8"))
    print(m.hexdigest())


main()
