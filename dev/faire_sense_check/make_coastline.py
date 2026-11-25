#!/usr/bin/env python3
"""Make the compact coastline the sense check draws its maps with and tests positions against.

Natural Earth's 1:50 million land polygons (public domain, https://www.naturalearthdata.com) are
rounded to 0.01 degrees (about 1 km), repeated points are dropped, and the result is written as
gzipped JSON: {"scale": 100, "polygons": [[ring, ...], ...]}, each ring a flat list of
longitude, latitude pairs times 100, the outer ring first.

Usage: python make_coastline.py ne_50m_land.geojson data/ne_50m_land.json.gz
       (the GeoJSON is in https://github.com/nvkelso/natural-earth-vector, geojson/)
"""
import gzip
import json
import sys


def main(src, out):
    g = json.load(open(src, encoding='utf-8'))
    polys = []
    for f in g['features']:
        geom = f['geometry']
        parts = geom['coordinates'] if geom['type'] == 'MultiPolygon' else [geom['coordinates']]
        for poly in parts:
            rings = []
            for ring in poly:
                pts, last = [], None
                for x, y in ring:
                    p = (round(x * 100), round(y * 100))
                    if p != last:
                        pts.append(p)
                        last = p
                if len(pts) >= 4:
                    rings.append([v for p in pts for v in p])
            if rings:
                polys.append(rings)
    data = json.dumps({'scale': 100, 'polygons': polys}, separators=(',', ':'))
    with gzip.open(out, 'wt', encoding='utf-8') as fh:
        fh.write(data)
    print(f'{len(polys)} polygons written to {out}')


if __name__ == '__main__':
    main(*sys.argv[1:3])
