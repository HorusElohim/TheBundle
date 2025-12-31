from pathlib import Path

import rich_click as click

from bundle.core import logger, tracer
from bundle.usd.map import OVERPASS_ENDPOINT, download_map

log = logger.get_logger(__name__)


def parse_center(_: click.Context, __: click.Parameter, value: str) -> tuple[float, float]:
    parts = [p.strip() for p in value.split(",")]
    if len(parts) != 2:
        raise click.BadParameter("center must be 'lon,lat'")
    lon = float(parts[0])
    lat = float(parts[1])
    return lat, lon


@click.group()
@tracer.Sync.decorator.call_raise
async def usd():
    """USD utilities."""
    pass


@usd.group()
@tracer.Sync.decorator.call_raise
async def map():
    """OpenStreetMap helpers."""
    pass


@map.command("download")
@click.option(
    "--center",
    default="2.3522,48.8566",
    callback=parse_center,
    show_default=True,
    help="Center lon,lat (e.g. 2.3522,48.8566).",
)
@click.option("--radius-km", default=5.0, type=float, show_default=True, help="Radius in kilometers.")
@click.option(
    "--highway",
    default="primary|secondary|tertiary|residential",
    show_default=True,
    help="OSM highway regex filter.",
)
@click.option("--no-buildings", is_flag=True, help="Disable building footprint polygons.")
@click.option("--width", type=float, default=6.0, show_default=True, help="Road width in meters.")
@click.option("--width-scale", type=float, default=1.0, show_default=True, help="Multiplier applied to road width.")
@click.option("--lane-width", type=float, default=0.6, show_default=True, help="Lane stripe width in meters (0 disables).")
@click.option("--lane-height", type=float, default=0.03, show_default=True, help="Lane stripe height offset.")
@click.option("--simplify", type=float, default=0.0, show_default=True, help="Simplify roads in meters (0 disables).")
@click.option(
    "--building-simplify",
    type=float,
    default=None,
    show_default=False,
    help="Simplify building footprints (defaults to --simplify).",
)
@click.option("--scale", type=float, default=1.0, show_default=True, help="Scale factor applied to coordinates.")
@click.option("--max-ways", type=int, default=0, show_default=True, help="Limit number of road ways (0 = no limit).")
@click.option("--max-buildings", type=int, default=0, show_default=True, help="Limit number of buildings (0 = no limit).")
@click.option("--output", default="data/paris_roads.usda", show_default=True, help="Output USD file path.")
@click.option("--endpoint", default=OVERPASS_ENDPOINT, show_default=True, help="Overpass API endpoint override.")
@click.option("--debug", is_flag=True, help="Enable debug logging.")
@tracer.Sync.decorator.call_raise
def download(
    center: tuple[float, float],
    radius_km: float,
    highway: str,
    no_buildings: bool,
    width: float,
    width_scale: float,
    lane_width: float,
    lane_height: float,
    simplify: float,
    building_simplify: float | None,
    scale: float,
    max_ways: int,
    max_buildings: int,
    output: str,
    endpoint: str,
    debug: bool,
):
    """Download OSM data and export a USD road scene."""
    if debug:
        log.setLevel("DEBUG")
    center_lat, center_lon = center
    download_map(
        center_lat=center_lat,
        center_lon=center_lon,
        radius_km=radius_km,
        highway_regex=highway,
        output=Path(output),
        include_buildings=not no_buildings,
        width=width,
        width_scale=width_scale,
        lane_width=lane_width,
        lane_height=lane_height,
        simplify=simplify,
        building_simplify=building_simplify,
        scale=scale,
        max_ways=max_ways,
        max_buildings=max_buildings,
        endpoint=endpoint,
        debug=debug,
    )


if __name__ == "__main__":
    usd()
