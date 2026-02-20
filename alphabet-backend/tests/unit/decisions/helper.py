from alphabet.experiments.domain.experiment import Variant, Percentage


def variant(name: str, value: str, audience: int = 50, is_control: bool = False) -> Variant:
    return Variant(name=name, value=value, is_control=is_control, audience=Percentage(audience))
