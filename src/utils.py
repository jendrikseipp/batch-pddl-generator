import logging
from pathlib import Path
import shutil
import sys

from domains import Domain


def generate_input_files(generators_dir, domain: Domain, parameters, seed, output_dir, timeout=None):
    # Write problem file.
    task_name = join_parameters(parameters)
    plan_dir = Path(output_dir) / task_name / str(seed)
    shutil.rmtree(plan_dir, ignore_errors=True)
    plan_dir.mkdir(parents=True)
    problem_file = plan_dir / "problem.pddl"
    domain_file = plan_dir / "domain.pddl"
    command = domain.get_generator_command(
        generators_dir, parameters, seed
    )
    logging.debug("Generator command: {}".format(" ".join(command)))
    with open(plan_dir / "generator-command.txt", "w") as f:
        print(" ".join(command), file=f)
    domain.generate_problem(command, problem_file, domain_file, timeout=timeout)

    if not domain_file.is_file():
        shutil.copy2(domain.get_domain_file(generators_dir), domain_file)
    assert problem_file.is_file()

    return plan_dir


def collect_task(domain, cfg, seed, srcdir, destdir, copy_logs=False):
    cfg_string = join_parameters(cfg)
    problem_name = f"p-{cfg_string}-{seed}.pddl"
    target_dir = destdir / domain.name
    target_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(srcdir / "problem.pddl", target_dir / problem_name)
    if copy_logs:
        try:
            shutil.copy2(srcdir / "run.log", target_dir / f"p-{cfg_string}-{seed}.log")
        except FileNotFoundError:
            shutil.copy2(srcdir / "run.log.xz", target_dir / f"p-{cfg_string}-{seed}.log.xz")

    # Copy domain file.
    output_domain_filename = "domain.pddl"
    if domain.uses_per_instance_domain_file():
        output_domain_filename = f"domain-p-{cfg_string}-{seed}.pddl"
    shutil.copy2(srcdir / "domain.pddl", target_dir / output_domain_filename)

    # Write information about parameters.
    order = ", ".join(str(k) for k in sorted(cfg))
    with open(target_dir / "README", "w") as f:
        print(f"Parameter order: {order}", file=f)


def join_parameters(parameters: dict):
    def format_value(value):
        if isinstance(value, str):
            value = value.strip("-")
            if not value:
                value = "empty"
        elif isinstance(value, float):
            value = f"{value:.2}"
        return str(value)
    return "-".join(format_value(value) for _, value in sorted(parameters.items()))


def check_generators_dir(generators_dir, domains):
    if not generators_dir.exists():
        sys.exit(f"Error: generators directory not found: {generators_dir}")
    for domain in domains:
        if (
            not (generators_dir / domain / "domain.pddl").is_file()
            and not domains[domain].uses_per_instance_domain_file()
        ):
            sys.exit(f"Error: domain.pddl missing for {domain}")


def setup_logging(debug):
    """
    Print DEBUG and INFO messages to stdout and higher levels to stderr.
    """
    # Python adds a default handler if some log is generated before here.
    # Remove all handlers that have been added automatically.
    logger = logging.getLogger("")
    for handler in logger.handlers:
        logger.removeHandler(handler)

    class InfoFilter(logging.Filter):
        def filter(self, rec):
            return rec.levelno in (logging.DEBUG, logging.INFO)

    logger.setLevel(logging.DEBUG if debug else logging.INFO)

    formatter = logging.Formatter("%(asctime)s %(levelname)-8s %(message)s")

    h1 = logging.StreamHandler(sys.stdout)
    h1.setLevel(logging.DEBUG)
    h1.addFilter(InfoFilter())
    h1.setFormatter(formatter)

    h2 = logging.StreamHandler()
    h2.setLevel(logging.WARNING)
    h2.setFormatter(formatter)

    logger.addHandler(h1)
    logger.addHandler(h2)
