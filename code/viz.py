#!/usr/bin/env python
import json
import sys
from pathlib import Path
from PIL import Image, ImageDraw


def main(problem, solution, output):
    with Path(problem).open() as fp:
        problem = json.load(fp)
    if solution:
        if not Path(solution).is_file():
            print('! not found', solution, file=sys.stderr)
            solution = None
        else:
            with Path(solution).open() as fp:
                solution = json.load(fp)
            
    rw = problem['room_width']
    rh = problem['room_height']
    sw = problem['stage_width']
    sh = problem['stage_height']
    ox,oy = problem['stage_bottom_left']
    mps = problem['musicians']
    ppl = problem['attendees']
    bps = problem['pillars']
    
    rw,rh,sw,sh,ox,oy = map(int, (rw,rh,sw,sh,ox,oy))
    
    im = Image.new('P', (rw, rh))
    im.putpalette([255,255,255, 211,210,208, 151,148,154, 241,154,154, 123,152,255, 173,10,10])
    draw = ImageDraw.Draw(im)
    draw.rectangle([ox, oy, ox+sw-1, oy+sh-1], fill=3)
    for p in bps:
        x,y,r = map(int, [p['center'][0], p['center'][1], p['radius']])
        draw.ellipse([x-r,y-r,x+r-1,y+r-1], fill=2)
    for p in ppl:
        x,y = map(int, [p['x'], p['y']])
        draw.ellipse([x-3,y-3,x+2,y+2], fill=4)
    if solution:
        for p in solution['placements']:
            x,y = map(int, [p['x'], p['y']])
            draw.ellipse([x-10,y-10,x+9,y+9], fill=5)
    im = im.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    so = Image.new('P', (rw+2, rh+2), color=1)
    so.putpalette(im.getpalette())
    so.paste(im, (1,1))
    so.save(output)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('problem', help='problem file')
    parser.add_argument('solution', nargs='?', help='solution file')
    parser.add_argument('-o', '--output', help='output file')
    args = parser.parse_args()
    main(
        problem=args.problem,
        solution=args.solution,
        output=args.output
    )
