from datetime import datetime

from alphabet.experiments.domain.dsl.dsl import compile_dsl, translate_dsl

dsl = 'now > 2027-01-01'

expr = compile_dsl(dsl)
print(expr({"version": "1.14.0", "now": datetime.now().timestamp()}).run())