import time

import docker
from playwright.sync_api import sync_playwright

from .config import (
    BROWSER_IMAGE,
    BROWSER_NETWORK,
    CDP_PORT,
    CONNECT_DELAY,
    CONNECT_RETRIES,
    CONTAINER_LABEL,
)


def sweep_stale_containers():
    """Remove any CloakBrowser containers left over from a previous worker that died
    without running its teardown. Safe for the single-worker setup the compose file
    runs; with multiple worker processes this would also kill a sibling's browser, so
    keep beat/concurrency at one or scope the label per worker before scaling out.
    """
    docker_client = docker.from_env()
    for container in docker_client.containers.list(
        all=True, filters={"label": f"app={CONTAINER_LABEL}"}
    ):
        try:
            container.remove(force=True)
        except Exception:
            pass


def spawn_browser():
    """Start a CloakBrowser container via the Docker SDK and connect to it over CDP.

    The container joins BROWSER_NETWORK and is reached by its docker-assigned name via
    that network's DNS. Returns (container, playwright driver, browser); the caller owns
    teardown of all three. Raises if the CDP endpoint never comes up.
    """
    docker_client = docker.from_env()
    # No restart_policy: the worker owns this container's lifecycle. A revived orphan
    # would just leak; stale ones are cleared by sweep_stale_containers on worker start.
    container = docker_client.containers.run(
        BROWSER_IMAGE,
        command="cloakserve",
        detach=True,
        security_opt=["seccomp=unconfined"],
        network=BROWSER_NETWORK,
        labels={"app": CONTAINER_LABEL},
    )
    container.reload()

    cdp_url = f"http://{container.name}:{CDP_PORT}"
    driver = sync_playwright().start()

    # The container is up but cloakserve needs a moment before CDP accepts connections;
    # poll until it does or the retry budget is exhausted.
    browser = None
    for _ in range(CONNECT_RETRIES):
        try:
            browser = driver.chromium.connect_over_cdp(cdp_url)
            break
        except Exception:
            time.sleep(CONNECT_DELAY)

    if browser is None:
        driver.stop()
        container.remove(force=True)
        raise RuntimeError(f"CloakBrowser at {cdp_url} not ready")

    return container, driver, browser
