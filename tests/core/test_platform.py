from bundle.core import platform_info, logger

log = logger.get_logger(__name__)


def test_platform_info():
    log.info("Platform Information:")
    log.info("%s", platform_info)
