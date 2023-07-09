#!/usr/bin/env python
import io
import json
import math
import re
import requests
import struct
import subprocess
import sys
import tempfile
import time
import tomllib
from pathlib import Path
from urllib.parse import urljoin


class Client:
    API_URL = 'https://api.icfpcontest.com'
    
    def __init__(self, headers):
        self.api_url = self.API_URL
        self.headers = headers
        self.backend = None
        self.timeout = (0.3, 10)

    def __enter__(self):
        self.backend = requests.Session()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        if (ses := self.backend) is not None:
            self.backend = None
            ses.close()

    def get_json(self, path, tries=3):
        url = urljoin(self.api_url, path)
        delay = 1
        for _ in range(tries):
            r = self.backend.get(url, headers=self.headers, timeout=self.timeout)
            if r.status_code != 200:
                time.sleep(delay)
                delay *= 1.5
            else:
                break
        r.raise_for_status()
        return r.json()
    
    def post_json(self, path, body):
        url = urljoin(self.api_url, path)
        r = self.backend.post(url, json=body, headers=self.headers, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def get_submission(self, sid):
        r = self.get_json(f'/submission?submission_id={sid}')
        return r['Success']['submission']
    
    def post_submission(self, pid, ans):
        body = {'problem_id':pid, 'contents': json.dumps(ans)}
        r = self.post_json('/submission', body)
        return r


def api_pack_problem(problem, scoring_mode, time_limit):
    def packi(x): return struct.pack('i', int(x))
    def mpacki(v): return b''.join(map(packi, v))
    def mpack2i(v): return b''.join(map(mpacki, v))
    def packf(x): return struct.pack('f', float(x))
    def mpackf(v): return b''.join(map(packf, v))
    def mpack2f(v): return b''.join(map(mpackf, v))
    
    rw = problem['room_width']
    rh = problem['room_height']
    sw = problem['stage_width']
    sh = problem['stage_height']
    ox,oy = problem['stage_bottom_left']
    mps = problem['musicians']
    ppl = problem['attendees']
    bps = problem['pillars']
    ks = len(set(mps))
    
    data = packi(rw) + packi(rh)
    data += packi(sw) + packi(sh)
    data += packi(ox) + packi(oy)
    data += packi(ks) + packi(len(mps))
    data += packi(len(ppl))
    data += packi(len(bps))
    data += packi(scoring_mode or 0)
    data += packi(time_limit or 0)
    data += mpacki(mps)
    data += mpack2i([[o['x'],o['y']] for o in ppl])
    data += mpack2i([o['tastes'] for o in ppl])
    data += mpack2i([*o['center'], o['radius']] for o in bps)
    return data

def api_unpack_answer(data):
    def unpackl(data):
        v, = struct.unpack('q', data[:8])
        return v
    def vunpackf(data):
        n, = struct.unpack('I', data[:4])
        return struct.unpack(f'{2*n}f', data[4:4+8*n])
    def vunpacki(data):
        n, = struct.unpack('I', data[:4])
        return struct.unpack(f'{n}i', data[4:4+4*n])

    score = unpackl(data)
    pos = vunpackf(data[8:])
    vol = vunpacki(data[12+len(pos)*4:])
    pos = [pos[i:i+2] for i in range(0, len(pos), 2)]
    ans = {'placements':[{'x':x, 'y':y} for x,y in pos]}
    if vol:
        ans['volumes'] = vol
    return score,ans


def score_solution(problem, solution):
    codes = Path(__file__).parent
    app = codes / 'score.py'
    p = subprocess.run([str(app), str(problem), str(solution)], stdout=subprocess.PIPE, encoding='utf-8')
    p.check_returncode()
    ans = int(p.stdout)
    return ans


def open_client():
    proj = Path(__file__).parent.parent
    env = proj / '.env'
    headers = None
    if env.is_file():
        with env.open('rb') as fp:
            config = tomllib.load(fp)
            headers = config.get('headers', dict())
    return Client(headers=headers)


def main(input, pid, solver, time_limit, no_submit):
    if pid is None:
        pid, = map(int, re.findall(r'(\d+)\.json', input))
    with Path(input).open() as fp:
        problem = json.load(fp)

    scoring_mode = 2 if pid > 55 else 1
        
    proj = Path(__file__).parent.parent
    fsol = proj / 'solves' / f'solution-{pid}.json'
    fimg = proj / 'solves' / f'solution-{pid}.png'
    fscore = proj / 'solves' / f'solution-{pid}.score.txt'
    fsubm = proj / 'solves' / f'solution-{pid}.submission.json'
    old_score = float(fscore.read_text()) if fscore.is_file() else float('-inf')
    
    msg = api_pack_problem(problem, scoring_mode, time_limit)

    if len(msg) < 10000:
        imsg = struct.pack('I', len(msg)) + msg
        p = subprocess.run([solver], input=imsg, stdout=subprocess.PIPE, stderr=sys.stderr)
    else:
        with tempfile.NamedTemporaryFile('wb') as fmsg:
            fmsg.write(msg)
            fmsg.flush()
            p = subprocess.run([solver, fmsg.name], stdout=subprocess.PIPE, stderr=sys.stderr)
    p.check_returncode()
    score, ans = api_unpack_answer(p.stdout)
    
    diff = score - old_score
    sdiff = f'{int(diff):+d}' if math.isfinite(diff) else diff
    print(f'{pid}: {score} ({sdiff})')

    if score < 0 or diff < 1000000:
        if fsol.is_file():
            fsol.touch()
        return
    
    with fsol.open('w') as fp:
        json.dump(ans, fp)

    viz = proj / 'code' / 'viz.py'
    subprocess.run([viz, str(input), str(fsol), '-o', str(fimg)])

    if no_submit:
        return
        
    with open_client() as cli:
        sid  = cli.post_submission(pid, ans)
        time.sleep(1)
        ss = cli.get_submission(sid)
        print(repr(ss))
        
    score = ss.get('score', dict())
    if isinstance(score, dict):
        if (sn := score.get('Success')) is None:
            if score.get('Failure'):
                sn = -1
        if sn is not None:
            with fscore.open('w') as fp:
                print(sn, end='', file=fp)
            fsubm.unlink(missing_ok=True)
            return
    with fsubm.open('w') as fp:
        json.dump(ss, fp)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('input', help='problem file')
    parser.add_argument('-t', '--time-limit', metavar='T', type=int, help='time limit')
    parser.add_argument('-a', '--action', metavar='A', default='./solve', help='solver executable')
    parser.add_argument('-i', '--pid', metavar='I', type=int, help='problem id')
    parser.add_argument('-n', '--no-submit', action='store_true', help='suppress submission')
    args = parser.parse_args()
    main(
        input=args.input,
        pid=args.pid,
        solver=args.action,
        time_limit=args.time_limit,
        no_submit=args.no_submit
    )