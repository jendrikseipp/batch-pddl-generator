#! /usr/bin/env python3

import argparse
import logging
from pathlib import Path
import shutil
import subprocess

import ConfigSpace
from ConfigSpace.util import generate_grid

import domains
import utils


DIR = Path(__file__).resolve().parent
REPO = DIR.parent
DOMAINS = domains.get_domains()
TMPDIR_NAME = "tmp"


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "generators_dir",
        help="Path to directory containing the PDDL generators",
    )
    parser.add_argument("domain", choices=DOMAINS, help="Domain name")
    parser.add_argument("destdir", help="Destination directory for benchmarks")
    parser.add_argument("--debug", action="store_true", help="Print debug info")
    parser.add_argument("--dry-run", action="store_true", help="Show only size of configuration space")
    parser.add_argument("--generator-time-limit", default=None, type=int, help="Time limit for generator calls")

    parser.add_argument(
        "--num-random-seeds",
        type=int,
        default=1,
        help="Number of random seeds used for each parameter configuration (default: %(default)d)",
    )

    return parser.parse_args()


def generate_task(generators_dir, domain, cfg, seed, tmp_dir, output_dir, time_limit=None):
    try:
        cfg = domain.adapt_parameters(cfg)
    except domains.IllegalConfiguration as err:
        logging.warning(f"Skipping illegal configuration {cfg}: {err}")
        return

    logging.info(f"Create instance for configuration {cfg} with seed {seed}")
    try:
        plan_dir = utils.generate_input_files(generators_dir, domain, cfg, seed, tmp_dir, timeout=time_limit)
    except subprocess.CalledProcessError as err:
        logging.error(f"Failed to generate task: {err}")
        return
    except subprocess.TimeoutExpired as err:
        logging.error(f"Failed to generate task: {err}")
        return

    utils.collect_task(domain, cfg, seed, srcdir=plan_dir, destdir=output_dir, copy_logs=False)


def main():
    args = parse_args()
    utils.setup_logging(args.debug)

    domain = DOMAINS[args.domain]
    generators_dir = Path(args.generators_dir)
    destdir = Path(args.destdir)
    tmp_dir = destdir / "tmp"

    # Build Configuration Space which defines all parameters and their ranges.
    cs = ConfigSpace.ConfigurationSpace()
    cs.add(domain.attributes)
    print(f"Parameters: {dict(cs)}")

    # Create num_steps_dict for generate_grid
    # For UniformIntegerHyperparameter, calculate steps based on the range
    # CategoricalHyperparameter will use all choices automatically
    # UniformFloatHyperparameter will use a reasonable default grid
    num_steps_dict = {}
    for hp_name, hp in dict(cs).items():
        if hasattr(hp, 'lower') and hasattr(hp, 'upper'):
            if hasattr(hp, 'step_size') and hp.step_size is not None:
                # Calculate number of steps based on step_size
                num_steps = int((hp.upper - hp.lower) / hp.step_size) + 1
                num_steps_dict[hp_name] = num_steps
            elif hp.__class__.__name__ == 'UniformIntegerHyperparameter':
                # For integer hyperparameters, use the full range (every integer value)
                num_steps_dict[hp_name] = hp.upper - hp.lower + 1
            # For continuous float hyperparameters, let ConfigSpace decide the grid size
        # Categorical hyperparameters automatically use all choices
    
    grid = generate_grid(cs, num_steps_dict)
    if args.dry_run:
        return
    for cfg in grid:
        cfg = dict(cfg)
        for seed in range(args.num_random_seeds):
            generate_task(
                generators_dir, domain, cfg, seed, tmp_dir, destdir,
                time_limit=args.generator_time_limit)
    shutil.rmtree(tmp_dir, ignore_errors=False)
    print(f"Number of configurations: {len(grid)}")


main()
