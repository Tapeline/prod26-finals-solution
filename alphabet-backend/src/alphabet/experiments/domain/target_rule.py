from typing import final

from alphabet.experiments.domain.dsl.dsl import translate_dsl
from alphabet.shared.commons import value_object


@final
@value_object
class TargetRuleString:
    value: str

    def validate(self) -> None:
        translate_dsl(self.value)
