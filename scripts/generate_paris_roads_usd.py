#!/usr/bin/env python3
"""
Generate a USD scene for Paris using OpenStreetMap Overpass.
Outputs separate meshes for roads, lane stripes, and building footprints.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Tuple

OVERPASS_ENDPOINT = "https://overpass-api.de/api/interpreter"


@dataclass(frozen=True)
class BBox:
    south: float
    west: float
    north: float
    east: float

    @classmethod
    def from_string(cls, value: str) -> "BBox":
        parts = [p.strip() for p in value.split(",")]
        if len(parts) != 4:
            raise ValueError("bbox must be 'south,west,north,east'")
        return cls(*(float(p) for p in parts))

    @property
    def center(self) -> Tuple[float, float]:
        return (self.south + self.north) / 2.0, (self.west + self.east) / 2.0


def fetch_overpass(query: str, endpoint: str) -> dict:
    data = urllib.parse.urlencode({"data": query}).encode("utf-8")
    request = urllib.request.Request(
        endpoint,
        data=data,
        headers={"User-Agent": "TheBundle-USD-Roads/1.0"},
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        payload = response.read().decode("utf-8")
    return json.loads(payload)


def build_query(bbox: BBox, highway_regex: str, include_buildings: bool) -> str:
    building_clause = ""
    if include_buildings:
        building_clause = f'  way["building"]({bbox.south},{bbox.west},{bbox.north},{bbox.east});'
    return f"""
[out:json][timeout:60];
(
  way["highway"~"{highway_regex}"]({bbox.south},{bbox.west},{bbox.north},{bbox.east});
  {building_clause}
);
(._;>;);
out body;
""".strip()


def latlon_to_local(lat: float, lon: float, lat0: float, lon0: float) -> Tuple[float, float]:
    # Equirectangular projection around the bbox center.
    earth_radius = 6378137.0
    lat_rad = math.radians(lat)
    lat0_rad = math.radians(lat0)
    x = (math.radians(lon - lon0)) * math.cos(lat0_rad) * earth_radius
    z = (math.radians(lat - lat0)) * earth_radius
    return x, z


def segments_from_way(nodes: List[int]) -> Iterable[Tuple[int, int]]:
    for i in range(len(nodes) - 1):
        yield nodes[i], nodes[i + 1]


def normalize(dx: float, dz: float) -> Tuple[float, float]:
    length = math.hypot(dx, dz)
    if length <= 1e-6:
        return 0.0, 0.0
    return dx / length, dz / length


def perp(dx: float, dz: float) -> Tuple[float, float]:
    return -dz, dx


def build_strip(
    polyline: List[Tuple[float, float]],
    half_width: float,
) -> List[Tuple[Tuple[float, float], Tuple[float, float]]]:
    if len(polyline) < 2:
        return []

    strip: List[Tuple[Tuple[float, float], Tuple[float, float]]] = []
    for i, (x, z) in enumerate(polyline):
        if i == 0:
            dx, dz = polyline[i + 1][0] - x, polyline[i + 1][1] - z
            dirx, dirz = normalize(dx, dz)
            n1x, n1z = perp(dirx, dirz)
            miterx, miterz = n1x, n1z
            scale = half_width
        elif i == len(polyline) - 1:
            dx, dz = x - polyline[i - 1][0], z - polyline[i - 1][1]
            dirx, dirz = normalize(dx, dz)
            n1x, n1z = perp(dirx, dirz)
            miterx, miterz = n1x, n1z
            scale = half_width
        else:
            dx1, dz1 = x - polyline[i - 1][0], z - polyline[i - 1][1]
            dx2, dz2 = polyline[i + 1][0] - x, polyline[i + 1][1] - z
            dir1x, dir1z = normalize(dx1, dz1)
            dir2x, dir2z = normalize(dx2, dz2)
            n1x, n1z = perp(dir1x, dir1z)
            n2x, n2z = perp(dir2x, dir2z)
            mixx, mixz = n1x + n2x, n1z + n2z
            miterx, miterz = normalize(mixx, mixz)
            if miterx == 0.0 and miterz == 0.0:
                miterx, miterz = n1x, n1z
                scale = half_width
            else:
                denom = miterx * n2x + miterz * n2z
                if abs(denom) < 0.1:
                    scale = half_width
                else:
                    scale = abs(half_width / denom)
                scale = min(scale, half_width * 4.0)

        left = (x + miterx * scale, z + miterz * scale)
        right = (x - miterx * scale, z - miterz * scale)
        strip.append((left, right))
    return strip


def add_strip(
    points: List[Tuple[float, float, float]],
    normals: List[Tuple[float, float, float]],
    counts: List[int],
    indices: List[int],
    strip: List[Tuple[Tuple[float, float], Tuple[float, float]]],
    y: float,
) -> None:
    for i in range(len(strip) - 1):
        left_a, right_a = strip[i]
        left_b, right_b = strip[i + 1]
        start = len(points)
        points.extend(
            [
                (left_a[0], y, left_a[1]),
                (left_b[0], y, left_b[1]),
                (right_b[0], y, right_b[1]),
                (right_a[0], y, right_a[1]),
            ]
        )
        normals.extend([(0.0, 1.0, 0.0)] * 4)
        counts.append(4)
        indices.extend([start, start + 1, start + 2, start + 3])


def polygon_area(poly: List[Tuple[float, float]]) -> float:
    area = 0.0
    for i in range(len(poly)):
        x1, z1 = poly[i]
        x2, z2 = poly[(i + 1) % len(poly)]
        area += x1 * z2 - x2 * z1
    return area / 2.0


def point_in_triangle(
    p: Tuple[float, float],
    a: Tuple[float, float],
    b: Tuple[float, float],
    c: Tuple[float, float],
) -> bool:
    px, pz = p
    ax, az = a
    bx, bz = b
    cx, cz = c
    v0x, v0z = cx - ax, cz - az
    v1x, v1z = bx - ax, bz - az
    v2x, v2z = px - ax, pz - az

    dot00 = v0x * v0x + v0z * v0z
    dot01 = v0x * v1x + v0z * v1z
    dot02 = v0x * v2x + v0z * v2z
    dot11 = v1x * v1x + v1z * v1z
    dot12 = v1x * v2x + v1z * v2z

    denom = dot00 * dot11 - dot01 * dot01
    if denom == 0.0:
        return False
    inv = 1.0 / denom
    u = (dot11 * dot02 - dot01 * dot12) * inv
    v = (dot00 * dot12 - dot01 * dot02) * inv
    return u >= 0.0 and v >= 0.0 and u + v <= 1.0


def point_line_distance(
    p: Tuple[float, float],
    a: Tuple[float, float],
    b: Tuple[float, float],
) -> float:
    px, pz = p
    ax, az = a
    bx, bz = b
    dx = bx - ax
    dz = bz - az
    if dx == 0.0 and dz == 0.0:
        return math.hypot(px - ax, pz - az)
    t = ((px - ax) * dx + (pz - az) * dz) / (dx * dx + dz * dz)
    t = max(0.0, min(1.0, t))
    projx = ax + t * dx
    projz = az + t * dz
    return math.hypot(px - projx, pz - projz)


def simplify_polyline(points: List[Tuple[float, float]], epsilon: float) -> List[Tuple[float, float]]:
    if epsilon <= 0.0 or len(points) < 3:
        return points
    start = points[0]
    end = points[-1]
    max_dist = 0.0
    index = 0
    for i in range(1, len(points) - 1):
        dist = point_line_distance(points[i], start, end)
        if dist > max_dist:
            max_dist = dist
            index = i
    if max_dist <= epsilon:
        return [start, end]
    left = simplify_polyline(points[: index + 1], epsilon)
    right = simplify_polyline(points[index:], epsilon)
    return left[:-1] + right


def triangulate_polygon(poly: List[Tuple[float, float]]) -> List[Tuple[int, int, int]]:
    if len(poly) < 3:
        return []
    indices = list(range(len(poly)))
    if polygon_area(poly) < 0:
        indices.reverse()

    triangles: List[Tuple[int, int, int]] = []
    guard = 0
    while len(indices) > 2 and guard < 10000:
        guard += 1
        ear_found = False
        for i in range(len(indices)):
            i_prev = indices[i - 1]
            i_curr = indices[i]
            i_next = indices[(i + 1) % len(indices)]
            ax, az = poly[i_prev]
            bx, bz = poly[i_curr]
            cx, cz = poly[i_next]
            cross = (bx - ax) * (cz - az) - (bz - az) * (cx - ax)
            if cross <= 0:
                continue
            ear = True
            for j in indices:
                if j in (i_prev, i_curr, i_next):
                    continue
                if point_in_triangle(poly[j], (ax, az), (bx, bz), (cx, cz)):
                    ear = False
                    break
            if not ear:
                continue
            triangles.append((i_prev, i_curr, i_next))
            del indices[i]
            ear_found = True
            break
        if not ear_found:
            break
    return triangles


def write_mesh(
    handle,
    name: str,
    points: List[Tuple[float, float, float]],
    normals: List[Tuple[float, float, float]],
    counts: List[int],
    indices: List[int],
    color: Tuple[float, float, float],
) -> None:
    if not points:
        return
    extent = compute_extent(points)
    handle.write(f'    def Mesh "{name}" {{\n')
    if extent:
        min_pt, max_pt = extent
        handle.write(
            "        float3[] extent = [(%0.3f, %0.3f, %0.3f), (%0.3f, %0.3f, %0.3f)]\n"
            % (min_pt[0], min_pt[1], min_pt[2], max_pt[0], max_pt[1], max_pt[2])
        )
    handle.write("        bool doubleSided = 1\n")
    handle.write('        uniform token subdivisionScheme = "none"\n')
    handle.write("        int[] faceVertexCounts = [\n")
    handle.write("            " + ", ".join(str(c) for c in counts) + "\n")
    handle.write("        ]\n")
    handle.write("        int[] faceVertexIndices = [\n")
    handle.write("            " + ", ".join(str(i) for i in indices) + "\n")
    handle.write("        ]\n")
    handle.write("        point3f[] points = [\n")
    for x, y, z in points:
        handle.write(f"            ({x:.3f}, {y:.3f}, {z:.3f}),\n")
    handle.write("        ]\n")
    if normals:
        handle.write("        normal3f[] normals = [\n")
        for x, y, z in normals:
            handle.write(f"            ({x:.3f}, {y:.3f}, {z:.3f}),\n")
        handle.write("        ]\n")
        handle.write('        uniform token normals:interpolation = "vertex"\n')
    handle.write("        color3f[] primvars:displayColor = [(%0.3f, %0.3f, %0.3f)]\n" % color)
    handle.write('        uniform token primvars:displayColor:interpolation = "constant"\n')
    handle.write("    }\n")


def write_usda(
    output_path: Path,
    road: dict,
    lanes: dict,
    buildings: dict,
) -> None:
    with output_path.open("w", encoding="utf-8") as handle:
        handle.write("#usda 1.0\n")
        handle.write('(\n    defaultPrim = "World"\n    metersPerUnit = 1.0\n    upAxis = "Y"\n)\n\n')
        handle.write('def Xform "World" {\n')
        write_mesh(
            handle,
            "Roads",
            road["points"],
            road["normals"],
            road["counts"],
            road["indices"],
            (0.38, 0.40, 0.44),
        )
        write_mesh(
            handle,
            "Lanes",
            lanes["points"],
            lanes["normals"],
            lanes["counts"],
            lanes["indices"],
            (0.94, 0.92, 0.78),
        )
        write_mesh(
            handle,
            "Buildings",
            buildings["points"],
            buildings["normals"],
            buildings["counts"],
            buildings["indices"],
            (0.25, 0.33, 0.5),
        )
        handle.write("}\n")


def compute_extent(points: List[Tuple[float, float, float]]):
    if not points:
        return None
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    zs = [p[2] for p in points]
    return (min(xs), min(ys), min(zs)), (max(xs), max(ys), max(zs))


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a USD road mesh for Paris from OpenStreetMap.")
    parser.add_argument(
        "--bbox",
        default="48.815,2.224,48.902,2.469",
        help="BBox south,west,north,east (default: central Paris).",
    )
    parser.add_argument(
        "--highway",
        default="primary|secondary|tertiary|residential",
        help="OSM highway regex filter.",
    )
    parser.add_argument(
        "--no-buildings",
        action="store_false",
        dest="include_buildings",
        default=True,
        help="Disable building footprint polygons.",
    )
    parser.add_argument(
        "--width",
        type=float,
        default=6.0,
        help="Road width in meters.",
    )
    parser.add_argument(
        "--width-scale",
        type=float,
        default=1.0,
        help="Multiplier applied to the road width.",
    )
    parser.add_argument(
        "--lane-width",
        type=float,
        default=0.6,
        help="Lane stripe width in meters (0 disables).",
    )
    parser.add_argument(
        "--lane-height",
        type=float,
        default=0.03,
        help="Lane stripe height offset to avoid z-fighting.",
    )
    parser.add_argument(
        "--simplify",
        type=float,
        default=0.0,
        help="Simplify roads by this tolerance in meters (0 disables).",
    )
    parser.add_argument(
        "--building-simplify",
        type=float,
        default=None,
        help="Simplify building footprints (defaults to --simplify).",
    )
    parser.add_argument(
        "--scale",
        type=float,
        default=1.0,
        help="Scale factor applied to coordinates.",
    )
    parser.add_argument(
        "--max-ways",
        type=int,
        default=0,
        help="Limit number of ways (0 = no limit).",
    )
    parser.add_argument(
        "--max-buildings",
        type=int,
        default=0,
        help="Limit number of buildings (0 = no limit).",
    )
    parser.add_argument(
        "--output",
        default="data/paris_roads.usda",
        help="Output USD file path.",
    )
    parser.add_argument(
        "--endpoint",
        default=OVERPASS_ENDPOINT,
        help="Overpass API endpoint.",
    )
    args = parser.parse_args()

    try:
        bbox = BBox.from_string(args.bbox)
    except ValueError as exc:
        print(f"Invalid bbox: {exc}", file=sys.stderr)
        return 1

    query = build_query(bbox, args.highway, args.include_buildings)
    print("Fetching OSM data from Overpass...")
    payload = fetch_overpass(query, args.endpoint)
    elements = payload.get("elements", [])

    nodes: dict[int, Tuple[float, float]] = {}
    ways: List[List[int]] = []
    building_ways: List[List[int]] = []
    for element in elements:
        if element.get("type") == "node":
            nodes[element["id"]] = (element["lat"], element["lon"])
        elif element.get("type") == "way":
            tags = element.get("tags", {})
            if "highway" in tags:
                ways.append(element.get("nodes", []))
            if args.include_buildings and "building" in tags:
                building_ways.append(element.get("nodes", []))

    if args.max_ways > 0:
        ways = ways[: args.max_ways]

    if not nodes or not ways:
        print("No road data returned. Try a different bbox or highway filter.", file=sys.stderr)
        return 1

    lat0, lon0 = bbox.center
    road_points: List[Tuple[float, float, float]] = []
    road_normals: List[Tuple[float, float, float]] = []
    road_counts: List[int] = []
    road_indices: List[int] = []
    lane_points: List[Tuple[float, float, float]] = []
    lane_normals: List[Tuple[float, float, float]] = []
    lane_counts: List[int] = []
    lane_indices: List[int] = []
    building_points: List[Tuple[float, float, float]] = []
    building_normals: List[Tuple[float, float, float]] = []
    building_counts: List[int] = []
    building_indices: List[int] = []
    half_width = args.width * args.width_scale / 2.0
    lane_half_width = args.lane_width / 2.0 if args.lane_width > 0 else 0.0

    for way_nodes in ways:
        polyline: List[Tuple[float, float]] = []
        for node_id in way_nodes:
            if node_id not in nodes:
                continue
            lat, lon = nodes[node_id]
            x, z = latlon_to_local(lat, lon, lat0, lon0)
            polyline.append((x * args.scale, z * args.scale))
        if args.simplify > 0:
            polyline = simplify_polyline(polyline, args.simplify)
        if len(polyline) < 2:
            continue
        strip = build_strip(polyline, half_width)
        if strip:
            add_strip(road_points, road_normals, road_counts, road_indices, strip, 0.0)
        if lane_half_width > 0:
            lane_strip = build_strip(polyline, lane_half_width)
            if lane_strip:
                add_strip(lane_points, lane_normals, lane_counts, lane_indices, lane_strip, args.lane_height)

    if args.include_buildings:
        building_simplify = args.simplify if args.building_simplify is None else args.building_simplify
        if args.max_buildings > 0:
            building_ways = building_ways[: args.max_buildings]
        for way_nodes in building_ways:
            if len(way_nodes) < 4 or way_nodes[0] != way_nodes[-1]:
                continue
            polyline: List[Tuple[float, float]] = []
            for node_id in way_nodes[:-1]:
                if node_id not in nodes:
                    continue
                lat, lon = nodes[node_id]
                x, z = latlon_to_local(lat, lon, lat0, lon0)
                polyline.append((x * args.scale, z * args.scale))
            if building_simplify and building_simplify > 0:
                polyline = simplify_polyline(polyline, building_simplify)
            if len(polyline) < 3:
                continue
            tris = triangulate_polygon(polyline)
            if not tris:
                continue
            base = len(building_points)
            for x, z in polyline:
                building_points.append((x, 0.0, z))
                building_normals.append((0.0, 1.0, 0.0))
            for a, b, c in tris:
                building_counts.append(3)
                building_indices.extend([base + a, base + b, base + c])

    if not road_points and not building_points:
        print("No usable road or building data found.", file=sys.stderr)
        return 1

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    write_usda(
        output_path,
        road={"points": road_points, "normals": road_normals, "counts": road_counts, "indices": road_indices},
        lanes={"points": lane_points, "normals": lane_normals, "counts": lane_counts, "indices": lane_indices},
        buildings={
            "points": building_points,
            "normals": building_normals,
            "counts": building_counts,
            "indices": building_indices,
        },
    )
    print(f"Wrote USD: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
