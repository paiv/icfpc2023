#!/usr/bin/env python
import http.client
import json
import logging
import requests
import sys
import tomllib
from pathlib import Path
from urllib.parse import urlparse, urljoin


VERBOSE = 1

if VERBOSE:
    http.client.HTTPConnection.debuglevel = 1
    logging.basicConfig()
    logging.getLogger().setLevel(logging.INFO)
    requests_log = logging.getLogger("urllib3")
    requests_log.setLevel(logging.INFO)
    requests_log.propagate = True


def trace(*args, **kwargs):
    if VERBOSE > 0: print(*args, file=sys.stderr, flush=True, **kwargs)
    

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

    def get_bytes(self, path):
        url = urljoin(self.api_url, path)
        r = self.backend.get(url, headers=self.headers, timeout=self.timeout)
        r.raise_for_status()
        return r.content

    
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

    def get_problems_count(self):
        r = self.get_json('/problems')
        return r['number_of_problems']
    
    def get_problem(self, pid):
        r = self.get_json(f'/problem?problem_id={pid}')
        s = r['Success']
        return json.loads(s)

    def cdn_problem(self, pid):
        url = f'https://cdn.icfpcontest.com/problems/{pid}.json'
        headers = self.headers.copy()
        headers.pop('Authorization', None)
        r = self.backend.get(url, headers=headers, timeout=self.timeout)
        r.raise_for_status()
        return r.content


def main(pid, last):
    env = Path(__file__).parent.parent / '.env'
    headers = None
    if env.is_file():
        with env.open('rb') as fp:
            config = tomllib.load(fp)
            headers = config.get('headers', dict())

    def write_problem(pid, obj):
        fn = Path(f'problem-{pid}.json')
        if isinstance(obj, bytes):
            with fn.open('wb') as fp:
                fp.write(obj)
        else:
            with fn.open('w') as fp:
                json.dump(obj, fp, separators=',:')
        
    with Client(headers=headers) as cli:
        if pid == 'all':
            n = cli.get_problems_count()
            trace('total problems', n)
            for pid in range(1,n+1):
                obj = cli.get_problem(pid)
                write_problem(pid, obj)
        elif last is not None:
            for pid in range(int(pid), int(last)+1):
                obj = cli.get_problem(pid)
                write_problem(pid, obj)
        else:
            obj = cli.cdn_problem(pid)
            write_problem(pid, obj)

    
if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('pid', help='problem id, or "all"')
    parser.add_argument('last', nargs='?', type=int, help='defines range, from pid to last')
    args = parser.parse_args()
    main(
        pid=args.pid,
        last=args.last
    )
