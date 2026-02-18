import os
import tomllib

with open("config.toml", "rb") as file:
    config = tomllib.load(file)
    db_url = config["tests"]["db_url"]
    app_url = config["tests"]["app_url"]
    redis_args = config["redis"]
    if os.environ.get("APP_URL"):
        app_url = os.environ["APP_URL"]
