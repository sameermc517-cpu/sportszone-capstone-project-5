"""
Shared pytest fixtures for the SportsZone Selenium end-to-end suite.

These tests drive a real browser against a fully deployed SportsZone
environment (all four services + database up and reachable) -- either
your local docker-compose stack, or the staging/production URL exposed
by Kubernetes in later phases of the capstone.

The target URL is never hard-coded: it is read from the BASE_URL
environment variable so the exact same test suite can run against
localhost during Phase 9 and against the real AWS load balancer URL
from the Jenkins pipeline in Phase 10.
"""

import os
import pytest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

BASE_URL = os.environ.get("BASE_URL", "http://localhost:5000")


@pytest.fixture(scope="session")
def base_url():
    return BASE_URL.rstrip("/")


@pytest.fixture
def driver():
    options = Options()
    # Headless is required in CI (Jenkins agents have no display) and is
    # also the recommended way to run this suite locally.
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1280,1024")

    drv = webdriver.Chrome(options=options)
    drv.implicitly_wait(5)
    yield drv
    drv.quit()
