"""
SportsZone Selenium End-to-End Test Suite
--------------------------------------------
Exercises the SportsZone platform exactly the way a real user would:
through the browser, against the web-frontend, which in turn talks to
the three backend microservices and the SQL database behind them.

Run with: BASE_URL=http://<your-deployed-frontend> pytest e2e-tests/ -v

These tests are intentionally ordered (test_01_, test_02_, ...) because
later tests depend on data created by earlier ones -- this mirrors a
real user's workflow: create a team, then a player on that team, then
a match between two teams, then update its score, and finally confirm
the dashboard reflects everything correctly.
"""

import time
from selenium.webdriver.common.by import By


def test_01_dashboard_loads(driver, base_url):
    driver.get(base_url + "/")
    assert "SportsZone" in driver.title or "SportsZone" in driver.page_source
    assert driver.find_element(By.CSS_SELECTOR, "h1")


def test_02_add_team_via_browser(driver, base_url):
    driver.get(base_url + "/")

    team_form = driver.find_element(By.CSS_SELECTOR, "form[action*='/teams/add']")
    team_form.find_element(By.NAME, "name").send_keys("Selenium Falcons")
    team_form.find_element(By.NAME, "city").send_keys("Testville")
    team_form.find_element(By.NAME, "sport").send_keys("Football")
    team_form.find_element(By.NAME, "founded_year").send_keys("1999")
    team_form.submit()

    time.sleep(1)
    assert "Selenium Falcons" in driver.page_source


def test_03_add_second_team(driver, base_url):
    driver.get(base_url + "/")
    team_form = driver.find_element(By.CSS_SELECTOR, "form[action*='/teams/add']")
    team_form.find_element(By.NAME, "name").send_keys("Selenium Eagles")
    team_form.find_element(By.NAME, "sport").send_keys("Football")
    team_form.submit()

    time.sleep(1)
    assert "Selenium Eagles" in driver.page_source


def test_04_add_player_against_existing_team(driver, base_url):
    driver.get(base_url + "/")
    player_form = driver.find_element(By.CSS_SELECTOR, "form[action*='/players/add']")
    player_form.find_element(By.NAME, "name").send_keys("Selenium Tester")
    player_form.find_element(By.NAME, "position").send_keys("QB")
    player_form.find_element(By.NAME, "jersey_no").send_keys("9")
    player_form.find_element(By.NAME, "team_id").send_keys("1")
    player_form.submit()

    time.sleep(1)
    assert "Selenium Tester" in driver.page_source


def test_05_schedule_match_between_two_teams(driver, base_url):
    driver.get(base_url + "/")
    match_form = driver.find_element(By.CSS_SELECTOR, "form[action*='/matches/add']")
    match_form.find_element(By.NAME, "home_team_id").send_keys("1")
    match_form.find_element(By.NAME, "away_team_id").send_keys("2")
    match_form.find_element(By.NAME, "venue").send_keys("Selenium Stadium")
    match_form.submit()

    time.sleep(1)
    assert "Selenium Stadium" in driver.page_source


def test_06_dashboard_reflects_full_workflow(driver, base_url):
    """After the previous steps, the dashboard should show one consistent
    picture pulled live from all three backend services and the database."""
    driver.get(base_url + "/")
    page = driver.page_source
    assert "Selenium Falcons" in page
    assert "Selenium Eagles" in page
    assert "Selenium Tester" in page
    assert "Selenium Stadium" in page


def test_07_invalid_player_team_shows_error_banner(driver, base_url):
    """Submitting a player against a non-existent team should surface the
    player-service's validation error back through the UI, not a crash."""
    driver.get(base_url + "/")
    player_form = driver.find_element(By.CSS_SELECTOR, "form[action*='/players/add']")
    player_form.find_element(By.NAME, "name").send_keys("Ghost Player")
    player_form.find_element(By.NAME, "team_id").send_keys("99999")
    player_form.submit()

    time.sleep(1)
    banners = driver.find_elements(By.CSS_SELECTOR, ".banner.error")
    assert len(banners) > 0, "Expected an error banner for an invalid team_id"
