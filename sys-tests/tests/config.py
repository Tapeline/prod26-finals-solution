import tomllib

with open("config.toml", "rb") as file:
    config = tomllib.load(file)
    db_url = config["tests"]["db_url"]
    app_url = config["tests"]["app_url"]
