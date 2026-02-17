from datetime import UTC, datetime

from alphabet.experiments.domain.dsl.dsl import compile_dsl

dsl = "now > 2027-01-01"

expr = compile_dsl(dsl)
print(expr({"version": "1.14.0", "now": datetime.now(UTC).timestamp()}).run())
