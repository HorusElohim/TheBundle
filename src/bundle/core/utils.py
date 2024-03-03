from datetime import timedelta, datetime


def format_duration_ns(ns: int) -> str:
    # Convert nanoseconds to microseconds for timedelta compatibility
    td = timedelta(microseconds=ns / 1000)

    units = [
        (td.days, "d"),
        (td.seconds // 3600, "h"),
        (td.seconds % 3600 // 60, "m"),
        (td.seconds % 60, "s"),
        (td.microseconds // 1000, "ms"),
        (td.microseconds % 1000, "µs"),  # Add microseconds
    ]

    time_str = ":".join(f"{value}{unit}" for value, unit in units if value > 0)

    # Append remaining nanoseconds for durations less than 1 microsecond
    remaining_ns = ns % 1000
    if remaining_ns > 0:
        time_str += f":{remaining_ns}ns"
    elif time_str == "":
        time_str = f"{ns}ns"

    return time_str


def format_date_ns(ns: int) -> str:
    # Convert nanoseconds to seconds for the datetime object
    dt = datetime.utcfromtimestamp(ns // 1_000_000_000)

    # Extract milliseconds, microseconds, and remaining nanoseconds
    milliseconds = (ns // 1_000_000) % 1_000
    microseconds = (ns // 1_000) % 1_000
    nanoseconds = ns % 1_000

    # Format the datetime object with milliseconds, microseconds, and nanoseconds
    return dt.strftime(f"%Y-%m-%d %H:%M:%S.{milliseconds:03d}.{microseconds:03d}.{nanoseconds:03d}")
