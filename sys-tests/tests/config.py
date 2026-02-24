import os
import tomllib

with open("config.toml", "rb") as file:
    config = tomllib.load(file)
    db_url = config["tests"]["db_url"]
    app_url = config["tests"]["app_url"]
    redis_args = config["redis"]
    click_args = config["clickhouse"]
    mailpit_url = config["tests"]["mailpit_url"]
    use_clear_endpoints = config["tests"]["use_clear_endpoints"]
    if os.environ.get("APP_URL"):
        app_url = os.environ["APP_URL"]
    if os.environ.get("MAILPIT_URL"):
        mailpit_url = os.environ["MAILPIT_URL"]
