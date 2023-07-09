#!/usr/bin/env python
import json
import math
import re
import sys
from pathlib import Path


def score_placement(placement, volumes, musicians, people, tastes, pillars, scoring_mode):
    ans = 0
    for j,(k,p) in enumerate(zip(musicians, placement)):
        sub = 0
        for i in range(len(people)):
            q = people[i]
            d = p - q
            d2 = d.real * d.real + d.imag * d.imag
            for z,pz in enumerate(placement):
                if z == j: continue
                tz = q - pz
                t = abs(d.real * tz.imag - tz.real * d.imag) 
                if t * t / d2 < 25 and abs(tz) < abs(d):
                    break
            else:
                t = tastes[i][k]
                sub += math.ceil(1000000 * t / d2)
        if scoring_mode == 2:
            qm = 1
            for z,(t,q) in enumerate(zip(musicians, placement)):
                if t == k and z != j:
                    d = p - q
                    qm += 1 / abs(d)
            ans += math.ceil(sub * qm * volumes[j])
        else:
            ans += sub * volumes[j]
    return ans


def main(problem, solution, scoring_mode, pid):
    if scoring_mode is None:
        if pid is None:
            if (ns := re.findall(r'(\d+)\.json', str(problem))):
                pid, = map(int, ns)
        scoring_mode = 2 if (pid or 0) > 55 else 1
        
    with Path(problem).open() as fp:
        problem = json.load(fp)
    with Path(solution).open() as fp:
        solution = json.load(fp)
    musicians = problem['musicians']
    people = [o['x'] + 1j * o['y'] for o in problem['attendees']]
    tastes = [o['tastes'] for o in problem['attendees']]
    pos = [o['x'] + 1j * o['y'] for o in solution['placements']]
    volumes = solution.get('volumes') or [1] * len(pos)
    pillars = [[o['center'][0] + 1j * o['center'][1], o['radius']] for o in problem['pillars']]
    ans = score_placement(pos, volumes, musicians, people, tastes, pillars, scoring_mode)
    print(ans)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('problem', help='problem file')
    parser.add_argument('solution', help='solution file')
    parser.add_argument('-m', '--scoring-mode', metavar='M', choices=(1,2), type=int, help='scoring mode, 1 lite, 2 full')
    parser.add_argument('-i', '--pid', metavar='I', type=int, help='problem id')
    args = parser.parse_args()
    main(
        problem=args.problem,
        solution=args.solution,
        scoring_mode=args.scoring_mode,
        pid=args.pid
    )
