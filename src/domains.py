from pathlib import Path
import shlex
import shutil
import subprocess
import sys

from ConfigSpace.hyperparameters import CategoricalHyperparameter
from ConfigSpace.hyperparameters import UniformFloatHyperparameter
from ConfigSpace.hyperparameters import UniformIntegerHyperparameter
from ConfigSpace.hyperparameters.constant import Constant


TMP_PROBLEM = "tmp-problem.pddl"
TMP_DOMAIN = "tmp-domain.pddl"


class IllegalConfiguration(Exception):
    pass


def get_int(name, lower, upper, *, log=False, step_size=1):
    if step_size == 1:
        # Use UniformIntegerHyperparameter for step_size=1 (continuous integer range)
        return UniformIntegerHyperparameter(
            name, lower=lower, upper=upper, default_value=lower, log=log
        )
    else:
        # Use CategoricalHyperparameter for step_size>1 (discrete values)
        choices = list(range(lower, upper + 1, step_size))
        return CategoricalHyperparameter(name, choices=choices, default_value=choices[0])


def get_float(name, lower, upper, *, log=False, precision=0.01):
    # For discrete float values with specific precision, create a categorical
    # hyperparameter with all valid values
    if precision is not None and precision > 0:
        import numpy as np
        # Generate all valid values within the range using the precision
        values = np.arange(lower, upper + precision/2, precision)
        # Round to avoid floating point precision issues
        values = np.round(values, decimals=10)
        # Convert to list and ensure we stay within bounds
        values = [float(v) for v in values if lower <= v <= upper]
        return CategoricalHyperparameter(name, choices=values, default_value=values[0])
    else:
        # For continuous float values, use UniformFloatHyperparameter
        return UniformFloatHyperparameter(
            name, lower=lower, upper=upper, default_value=lower, log=log
        )


def get_enum(name, choices, default_value=None):
    if default_value is None:
        default_value = choices[0]
    return CategoricalHyperparameter(name, choices, default_value=default_value)


class Domain:
    def __init__(self, name, generator_command, attributes, adapt_parameters=None):
        self.name = name
        self.attributes = attributes
        self.command_template = generator_command
        self._adapt_parameters = adapt_parameters

    def get_domain_file(self, generators_dir):
        return Path(generators_dir) / self.name / "domain.pddl"

    def adapt_parameters(self, parameters):
        if self._adapt_parameters:
            parameters = self._adapt_parameters(parameters.copy())
        return parameters

    def get_generator_command(self, generators_dir, parameters, seed):
        command = shlex.split(self.command_template.format(seed=seed, **parameters))
        command[0] = str((Path(generators_dir) / self.name / command[0]).resolve())
        # Call Python scripts with the correct Python interpreter.
        if command[0].endswith(".py"):
            command.insert(0, sys.executable)
        return command

    def generate_problem(self, command, problem_file, domain_file, timeout=None):
        # Some generators print to a file, others print to stdout.
        if TMP_PROBLEM in self.command_template:
            subprocess.run(command, check=True, timeout=timeout)
            shutil.move(TMP_PROBLEM, problem_file)
        else:
            with open(problem_file, "w") as f:
                subprocess.run(command, stdout=f, check=True, timeout=timeout)

        if self.uses_per_instance_domain_file():
            shutil.move(TMP_DOMAIN, domain_file)

    def uses_per_instance_domain_file(self):
        return TMP_DOMAIN in self.command_template


def adapt_parameters_barman(parameters):
    if parameters["shots"] < parameters["cocktails"]:
        raise IllegalConfiguration("we need shots >= cocktails")
    return parameters


def adapt_parameters_floortile(parameters):
    parameters["robots"] = min(parameters["robots"], parameters["columns"])
    return parameters


def adapt_parameters_freecell(parameters):
    if parameters["initial_stacks"] > parameters["columns"]:
        raise IllegalConfiguration("we need initial_stacks <= columns")
    return parameters


def adapt_parameters_grid(parameters):
    parameters["shapes"] = min(
        parameters["x"] * parameters["y"] - 1, parameters["shapes"]
    )
    parameters["keys"] = min(
        parameters["x"] * parameters["y"] - 1,
        parameters["shapes"] + parameters["extra_keys"],
    )
    parameters["locks"] = int(
        parameters["x"] * parameters["y"] * parameters["percentage_cells_locked"]
    )
    parameters["locks"] = max(parameters["locks"], parameters["shapes"])
    return parameters


def adapt_parameters_hiking(parameters):
    if parameters["cars"] < parameters["couples"] + 1:
        raise IllegalConfiguration("we need cars >= couples + 1")
    return parameters


def adapt_parameters_maintenance(parameters):
    parameters["planes"] = 3 * parameters["days"]
    parameters["mechanics"] = 1
    parameters["cities"] = 3
    parameters["visits"] = 5
    return parameters


def adapt_parameters_spanner(parameters):
    if parameters["spanners"] < parameters["nuts"]:
        raise IllegalConfiguration("we need spanners >= nuts")
    return parameters


def adapt_parameters_sokoban(parameters):
    grid_size = parameters["grid_size"]
    if grid_size <= 5:
        bound = 2
    else:
        bound = (grid_size * grid_size - 5 * grid_size + 6) / 9.0

    if parameters["boxes"] > bound:
        raise IllegalConfiguration(f"we need boxes <= {bound}")
    return parameters


def adapt_parameters_tetris(parameters):
    if parameters["rows"] % 2 == 1:
        raise IllegalConfiguration("number of rows must be even")
    return parameters


def adapt_parameters_tidybot(parameters):
    if parameters["mintablesize"] > parameters["maxtablesize"]:
        raise IllegalConfiguration("mintablesize must be <= maxtablesize")
    return parameters


DOMAINS = [
    Domain(
        "agricola",
        "GenAgricola.py {stages} {seed} --num_workers {workers} {all_workers_flag}",
        # Exclude --num_ints and --num_rounds {num_rounds} because they were not used in IPC'18.
        [
            get_int("stages", lower=3, upper=20),
            get_int("workers", lower=3, upper=20),
            get_enum(
                "all_workers_flag", ["", "--must_create_workers"], default_value=""
            ),
        ],
    ),
    Domain(
        "barman",
        "barman-generator.py {cocktails} {ingredients} {shots} {seed}",
        [
            get_int("cocktails", lower=1, upper=10),
            get_int("shots", lower=1, upper=5),
            get_int("ingredients", lower=2, upper=6),
        ],
        adapt_parameters=adapt_parameters_barman,
    ),
    Domain(
        "blocksworld",
        "blocksworld 4 {n} {seed}",
        [get_int("n", lower=2, upper=100)],
    ),
    Domain(
        "briefcaseworld",
        "briefcaseworld -o {objects} -s {seed}",
        [
            get_int("objects", lower=1, upper=100),
        ],
    ),
    Domain(
        "childsnack",
        "child-snack-generator.py pool {seed} {children} {trays} {gluten_factor} {constrainedness}",
        [
            get_int("children", lower=2, upper=5),
            get_float("constrainedness", lower=1.0, upper=2.0, precision=0.5),
            get_int("trays", lower=1, upper=3),
            get_float("gluten_factor", lower=0.2, upper=0.8, precision=0.2),
        ],
    ),
    Domain(
        "depots",
        "depots -e {depots} -i {distributors} -t {trucks} -p {pallets} -h {hoists} -c {crates} -s {seed}",
        [
            # IPC instances:
            # depots from 1 to 6
            # distributors from 2 to 6
            # trucks from 2 to 6
            # pallets from 3 to 20
            # hoists from 3 to 15
            # crates from 2 to 20
            get_int("depots", lower=1, upper=3),
            get_int("distributors", lower=2, upper=3),
            get_int("trucks", lower=2, upper=4),
            get_int("pallets", lower=3, upper=8),
            get_int("hoists", lower=3, upper=8),
            get_int("crates", lower=2, upper=7),
        ],
    ),
    Domain(
        "driverlog",
        "dlgen {seed} {roadjunctions} {drivers} {packages} {trucks}",
        [
            get_int("drivers", lower=1, upper=3),
            get_int("packages", lower=1, upper=3),
            get_int("roadjunctions", lower=2, upper=6),
            get_int("trucks", lower=1, upper=5),
        ],
    ),
    Domain(
        "ferry",
        "ferry -l {locations} -c {cars} -s {seed}",
        [
            get_int("locations", lower=1, upper=30),
            get_int("cars", lower=1, upper=30),
        ],
    ),
    Domain(
        "floortile",
        "floortile-generator.py name {rows} {columns} {robots} seq {seed}",
        [
            get_int("rows", lower=2, upper=6),
            get_int("columns", lower=2, upper=6),
            get_int("robots", lower=1, upper=6),
        ],
        adapt_parameters=adapt_parameters_floortile,
    ),
    Domain(
        "freecell",
        "freecell -f {cells} -c {columns} -s 4 -0 {suite_size} -1 {suite_size} "
        "-2 {suite_size} -3 {suite_size} -i {initial_stacks} -r {seed}",
        [
            get_int("cells", lower=2, upper=4),
            get_int("columns", lower=3, upper=8),
            #get_int("suits", lower=4, upper=4),  # hardcoded as in IPC tasks
            get_int("suite_size", lower=2, upper=20),
            get_int("initial_stacks", lower=1, upper=8),
        ],
        adapt_parameters=adapt_parameters_freecell,
    ),
    Domain(
        "fridge",
        "fridge -f {fridges} -s {screws} -r {seed}",
        [
            get_int("fridges", lower=1, upper=30),
            get_int("screws", lower=1, upper=30),
        ],
    ),
    Domain(
        "grid",
        "generate.py {x} {y} --shapes {shapes} --keys {keys} --locks {locks} --prob-goal {prob_key_in_goal} --seed {seed}",
        [
            get_int("x", lower=2, upper=5, step_size=1),
            get_int("y", lower=2, upper=5, step_size=1),
            get_float("prob_key_in_goal", lower=0.5, upper=1.0, precision=0.5),
            get_int("shapes", lower=1, upper=2),
            get_int("extra_keys", lower=1, upper=2),
            get_float("percentage_cells_locked", lower=0.3, upper=0.9, precision=0.3),
        ],
        adapt_parameters=adapt_parameters_grid,
    ),
    Domain(
        "hiking",
        "generator.py {couples} {cars} {places} {seed}",
        [
            get_int("couples", lower=1, upper=5),
            get_int("places", lower=2, upper=10),
            get_int("cars", lower=1, upper=5),
        ],
        adapt_parameters=adapt_parameters_hiking,
    ),
    Domain(
        "maintenance",
        "maintenance {days} {planes} {mechanics} {cities} {visits} {seed}",
        [
            get_int("days", lower=60, upper=300, step_size=20),
        ],
        adapt_parameters=adapt_parameters_maintenance,
    ),
    Domain(
        "movie",
        "movie -n {snacks}",
        [
            get_int("snacks", lower=1, upper=100),
        ]
    ),
    Domain(
        "mprime",
        "mprime -l {locations} -f {maxfuel} -s {maxspace} -v {vehicles} -c {cargos} -r {seed}",
        [
            # optimal planning (ranges from IPC renamed domain version):
            #   for file in `ls prob*.pddl`; do grep location $file | wc -l; done | sort -n | uniq | paste -s -d,
            #get_int("locations", lower=4, upper=22, step_size=1),  # 4,5,6,7,8,10,11,12,13,15,16,17,18,19,21,22
            #get_int("maxfuel", lower=3, upper=13, step_size=1),  # 3,4,5,6,7,8,9,10,11,12,13
            #get_int("maxspace", lower=1, upper=3, step_size=1),  # 1,2,3
            #get_int("vehicles", lower=1, upper=16, step_size=1),  # 1,2,3,4,5,6,7,8,9,11,16
            #get_int("cargos", lower=2, upper=46, step_size=1),  # 2,3,4,5,6,7,8,9,10,11,13,14,15,16,18,20,22,24,34,37,39,40,44,46
            get_enum("locations", [3,4,5,6,8,10]),
            get_enum("maxfuel", [3,4,5,6,8,10]),
            get_enum("maxspace", [1,2,3]),
            get_enum("vehicles", [1,2,3,4,6,8]),
            get_enum("cargos", [1,2,3,4,5,6,8,10,12]),
            # satisficing planning
            #get_int("locations", lower=5, upper=25, step_size=5),
            #get_int("maxfuel", lower=10, upper=15, step_size=5),
            #get_int("maxspace", lower=2, upper=4, step_size=2),
            #get_int("vehicles", lower=2, upper=16, step_size=2),
            #get_int("cargos", lower=5, upper=50, step_size=5),
        ],
    ),
    Domain(
        "mystery",
        "mystery -l {locations} -f {maxfuel} -s {maxspace} -v {vehicles} -c {cargos} -r {seed}",
        [
            get_int("locations", lower=5, upper=25, step_size=5),
            get_int("maxfuel", lower=10, upper=15, step_size=5),
            get_int("maxspace", lower=2, upper=4, step_size=2),
            get_int("vehicles", lower=2, upper=16, step_size=2),
            get_int("cargos", lower=5, upper=50, step_size=5),
        ],
    ),
    Domain(
        "npuzzle",
        "n-puzzle-generator -n {size} -s {seed}",
        [
            # get_int("size", lower=3, upper=3),
            Constant("size", 3),
        ],
    ),
    Domain(
        "pathways",
        f"wrapper.py --seed {{seed}} --reactions {{reactions}} --goals {{goals}} --initial-substances {{substances}} {TMP_DOMAIN} {TMP_PROBLEM}",
        [
            # optimal planning
            #get_int("reactions", lower=1, upper=101, step_size=5),  # IPC: 12-480
            #get_int("goals", lower=1, upper=31, step_size=3),  # IPC: 1-40
            #get_int("substances", lower=1, upper=22, step_size=3),  # IPC: 3-35
            # satisficing planning
            get_int("reactions", lower=10, upper=1010, step_size=50),  # IPC: 12-480
            get_int("goals", lower=10, upper=90, step_size=10),  # IPC: 1-40
            get_int("substances", lower=10, upper=80, step_size=10),  # IPC: 3-35
        ],
    ),
    Domain(
        "sokoban",
        "random/sokoban-generator-typed -n {grid_size} -b {boxes} -w {walls} -s {seed}",
        [
            get_int("grid_size", lower=5, upper=10),
            get_int("boxes", lower=1, upper=10),
            get_int("walls", lower=0, upper=10),
        ],
        adapt_parameters=adapt_parameters_sokoban,
    ),
    Domain(
        "tetris",
        "generator.py {rows} {block_type} {seed}",
        [
            get_int("rows", lower=4, upper=50),
            get_enum("block_type", ["1", "2", "3", "4"], "1"),
        ],
        adapt_parameters=adapt_parameters_tetris,
    ),
    Domain(
        "tidybot",
        "gentidy.py {worldsize} {tables} {cupboards} {mintablesize} {maxtablesize} {cupboardsize} {seed}",
        [
            get_int("worldsize", lower=5, upper=15, step_size=1),  # IPC 2011: 5-9 (opt), 9-12 (sat)
            get_int("tables", lower=0, upper=10, step_size=2),  # IPC 2011: 0-5 (opt), 2-9 (sat)
            get_int("cupboards", lower=1, upper=3),  # IPC 2011: 1 (opt), 1-3 (sat)
            get_int("mintablesize", lower=1, upper=5, step_size=2),  # IPC 2011: ? (opt), ? (sat)
            get_int("maxtablesize", lower=1, upper=5, step_size=2),  # IPC 2011: ? (opt), ? (sat)
            get_int("cupboardsize", lower=4, upper=5),  # IPC 2011: ? (opt), ? (sat), 4 (README)
        ],
        adapt_parameters=adapt_parameters_tidybot,
    ),
    # Schedule
    #
    # -p <num>    number of parts (minimal 1)
    # -s <num>    number of shapes (preset: 0, maximal: 2)
    # -c <num>    number of colors (preset: 2, minimal 1, maximal: 4)
    # -w <num>    number of widths (preset: 2, minimal 1, maximal: 3)
    # -o <num>    number of orientations (preset: 2, minimal 1, maximal: 2)
    # -Q <num>    probability cylindrical goal (preset: 80)
    # -W <num>    probability of colour in I (preset: 50)
    # -E <num>    probability of colour in G (preset: 80)
    # -R <num>    probability of hole in I (preset: 50)
    # -T <num>    probability of hole in G (preset: 80)
    # -Y <num>    probability of surface condition in G (preset: 50)
    # -r <num>    random seed (minimal 1, optional)
    Domain(
        "schedule",
        "./schedule "
        "-p {parts} -s {shapes} -c {colors} -w {widths} -o {orientations} "
        "-Q {prob_cylindrical_goal} -W {prob_color_init} -E {prob_color_goal} "
        "-R {prob_hole_init} -T {prob_hole_goal} -Y {prob_surface_goal} -r {seed}",
        [
            get_int("parts", lower=1, upper=3),
            get_int("shapes", lower=0, upper=1, log=False),
            get_int("colors", lower=1, upper=2, log=False),
            get_int("widths", lower=1, upper=2, log=False),
            get_int("orientations", lower=1, upper=2, log=False),
            get_int("prob_cylindrical_goal", lower=0, upper=100, log=True, step_size=30),
            get_int("prob_color_init", lower=0, upper=100, log=False, step_size=30),
            get_int("prob_color_goal", lower=0, upper=100, log=False, step_size=30),
            get_int("prob_hole_init", lower=0, upper=100, log=False, step_size=30),
            get_int("prob_hole_goal", lower=0, upper=100, log=False, step_size=30),
            get_int("prob_surface_goal", lower=0, upper=100, log=False, step_size=30),
        ],
    ),
    Domain(
        "spanner",
        "spanner-generator.py --seed {seed} {spanners} {nuts} {locations}",
        [
            get_int("spanners", lower=1, upper=5),
            get_int("nuts", lower=1, upper=5),
            get_int("locations", lower=1, upper=10),
        ],
        adapt_parameters=adapt_parameters_spanner,
    ),
    Domain(
        "tpp",
        "tpp -s {seed} -m {markets} -p {products} -t {trucks} -d {depots} -l {goods} "
        + TMP_PROBLEM,
        [
            get_int("products", lower=2, upper=20),
            get_int("markets", lower=1, upper=10),
            get_int("trucks", lower=2, upper=10),
            get_int("depots", lower=1, upper=10),
            get_int("goods", lower=3, upper=10),
        ],
    ),
    Domain(
        "tsp",
        "tsp -n {locations}",
        [
            get_int("locations", lower=2, upper=20),
        ],
    ),
    Domain(
        "visitall",
        "grid -x {grid_width} -y {grid_height} -u {unavailable_cells} -r {ratio_goal_cells} -s {seed}",
        [
            get_int("grid_width", lower=2, upper=3),
            get_int("grid_height", lower=2, upper=3),
            get_enum("unavailable_cells", [0]),
            get_float("ratio_goal_cells", lower=0.5, upper=1.0, precision=0.5),
        ]
    ),
]


def get_domains():
    return {domain.name: domain for domain in DOMAINS}
