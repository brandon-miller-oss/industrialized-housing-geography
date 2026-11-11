"""Albers USA projection (d3.geoAlbersUsa, scale 1300, translate [487.5, 305]) for points."""
from math import radians, sin, cos, sqrt

def _conic(p0, p1, rot, center, k, tx, ty):
    y0, y1 = radians(p0), radians(p1)
    n = (sin(y0) + sin(y1)) / 2
    c = 1 + sin(y0) * (2 * n - sin(y0))
    r0 = sqrt(c) / n
    def raw(lon, lat):
        x, y = radians(lon), radians(lat)
        r = sqrt(c - 2 * n * sin(y)) / n
        return r * sin(x * n), r0 - r * cos(x * n)
    cx, cy = raw(*center)
    def f(lon, lat):
        lon = ((lon + rot + 180) % 360) - 180
        x, y = raw(lon, lat)
        return tx + k * (x - cx), ty - k * (y - cy)
    return f

K, TX, TY = 1300, 487.5, 305
LOWER48 = _conic(29.5, 45.5, 96, (-0.6, 38.7), K, TX, TY)
ALASKA = _conic(55, 65, 154, (-2, 58.5), 0.35 * K, TX - 0.307 * K, TY + 0.201 * K)
HAWAII = _conic(8, 18, 157, (-3, 19.9), K, TX - 0.205 * K, TY + 0.212 * K)

def project(lat, lon):
    if lat > 50 and lon < -129:
        return ALASKA(lon, lat)
    if lat < 23 and lon < -150:
        return HAWAII(lon, lat)
    if 24 <= lat <= 50 and -125.5 <= lon <= -66:
        return LOWER48(lon, lat)
    return None
