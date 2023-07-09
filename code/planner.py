#!/usr/bin/env python
import re
import subprocess
import sys
from pathlib import Path


def planner(problems, solutions):
    while True:
        tasks = list()
        for fn in problems.glob('*.json'):
            pid, = re.findall(r'(\d+)\.json', str(fn))
            psize = fn.stat().st_size
            sol = solutions / f'solution-{pid}.json'
            fscore = solutions / f'solution-{pid}.score.txt'
            fsubm = solutions / f'solution-{pid}.submission.json'
            if fsubm.is_file():
                ts = fsubm.stat().st_mtime
                tasks.append((0, (ts, psize, pid, fsubm), 1))
                continue
            sol_time = 0
            if sol.is_file():
                sol_time = sol.stat().st_mtime
            tasks.append((0, (sol_time, psize, pid, fn), 0))
        tasks = sorted(tasks)
        if tasks:
            yield tasks[0]
        else:
            return


def run_solver(mtime, sz, pid, fn, time_limit):
    solver = Path(__file__).parent / 'solve.py'
    p = subprocess.run([str(solver), str(fn), '-t', time_limit or '0'], stdout=sys.stdout, stderr=sys.stderr)
    p.check_returncode()


def check_submission(mtime, sz, pid, fn):
    prog = Path(__file__).parent / 'check_submission.py'
    p = subprocess.run([str(prog), str(fn), '--pid', str(pid)])
    p.check_returncode()


def run_task(task, timeout):
    print('run', task)
    _,op,id = task
    match id:
        case 0:
            run_solver(*op, time_limit=timeout)
        case 1:
            check_submission(*op)
    

def main(problems, solutions, timeout):
    for task in planner(Path(problems), Path(solutions)):
        run_task(task, timeout)    


if __name__ == '__main__':
    proj = Path(__file__).parent.parent
    taskdir = proj / 'task'
    solvdir = proj / 'solves'
    
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--problems-directory', default=taskdir, help='problems directory, default ' + str(taskdir))
    parser.add_argument('-s', '--solutions-directory', default=solvdir, help='solutions directory, default ' + str(solvdir))
    parser.add_argument('-t', '--timeout', help='task timeout')
    args = parser.parse_args()
    main(
        problems=args.problems_directory,
        solutions=args.solutions_directory,
        timeout=args.timeout
    )