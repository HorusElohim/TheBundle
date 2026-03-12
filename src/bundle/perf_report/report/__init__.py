from .cprofile import generate_report as generate_cprofile_report
from .tracy import generate_report as generate_tracy_report

__all__ = ["generate_cprofile_report", "generate_tracy_report"]
