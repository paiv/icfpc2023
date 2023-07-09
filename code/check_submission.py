#!/usr/bin/env python
import json
import requests
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

    def get_json(self, path):
        url = urljoin(self.api_url, path)
        r = self.backend.get(url, headers=self.headers, timeout=self.timeout)
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


def open_client():
    proj = Path(__file__).parent.parent
    env = proj / '.env'
    headers = None
    if env.is_file():
        with env.open('rb') as fp:
            config = tomllib.load(fp)
            headers = config.get('headers', dict())
    return Client(headers=headers)

    
def main(input, pid):
    if pid is None:
        pid, = map(int, re.findall(r'(\d+)\.json', input))
    with Path(input).open() as fp:
        submission = json.load(fp)
        sid = submission['_id']
        
    proj = Path(__file__).parent.parent
    fscore = proj / 'solves' / f'solution-{pid}.score.txt'
    fsubm = proj / 'solves' / f'solution-{pid}.submission.json'

    with open_client() as cli:
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
    parser.add_argument('input', help='submission file')
    parser.add_argument('-i', '--pid', metavar='I', type=int, help='problem id')
    args = parser.parse_args()
    main(
        input=args.input,
        pid=args.pid
    )