from typing import final

from alphabet.shared.commons import dto


@final
@dto
class Pagination:
    limit: int
    offset: int
