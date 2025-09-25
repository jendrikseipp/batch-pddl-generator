# Batch PDDL Generator (BPG)

Specify PDDL generator parameters and their value ranges and let BPG generate
PDDL tasks for you.


## Installation

### Using uv (recommended)

Install [uv](https://docs.astral.sh/uv/) and then:

    uv sync

This will create a virtual environment and install all dependencies.

### Using pip (traditional)

Create a virtual environment:

    python3 -m venv --prompt sig .venv
    source .venv/bin/activate
    pip install -U pip wheel
    pip install -r requirements.txt

Clone repo with PDDL generators, and build the generators:

    git clone git@github.com:AI-Planning/pddl-generators.git
    cd pddl-generators
    ./build_all
    

## Usage

There are two ways in which this library can be used:

1. Generate the Cartesian product of instances over the given parameter values.

    For example, when you specify the following domain

        Domain(
            "tetris",
            "generator.py {rows} {block_type} {seed}",
            [
                get_int("rows", lower=4, upper=8, step_size=2),
                get_enum("block_type", ["1", "2", "3"], "1"),
            ],
        ),

    the command

        # Using uv:
        uv run python src/generate-instances.py \
            --generators-dir <path/to/generators> \
            tetris /tmp/tasks

        # Or using traditional Python:
        python src/generate-instances.py \
            --generators-dir <path/to/generators> \
            tetris /tmp/tasks

    will generate instances at /tmp/tasks for the following combination of
    rows and blocks:

        [(4, 1), (4, 2), (4, 3), (6, 1), (6, 2), (6, 3), (8, 1), (8, 2), (8, 3)]


2. Use SMAC to generate planning tasks that can be solved by a given planner
within given resource limits.

        # Using uv:
        uv run python src/search-instances-for-planner.py \
            --generators-dir <path/to/generators> \
            --planner-time-limit 60 \
            tetris <path/to/singularity-planner.img>

        # Or using traditional Python:
        python src/search-instances-for-planner.py \
            --generators-dir <path/to/generators> \
            --planner-time-limit 60 \
            tetris <path/to/singularity-planner.img>


## Finding Duplicate Tasks

After generating the benchmark tasks, you might want to run the
`find-duplicate-instances.py` script to detect duplicates.
