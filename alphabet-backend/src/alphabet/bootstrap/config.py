from fuente import config_loader
from fuente.sources.env import EnvSource
from fuente.sources.yaml import YamlSource

from alphabet.shared.config import Config

service_config_loader = config_loader(
    YamlSource("alphabet.yml"),
    EnvSource(prefix="AB_", sep="__"),
    config=Config,
)
