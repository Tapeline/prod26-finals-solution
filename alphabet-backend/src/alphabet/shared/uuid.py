import uuid7


def generate_uuid() -> str:
    return f"{uuid7.create()}"


def generate_id[Id_T](id_class: type[Id_T]) -> Id_T:
    return id_class(generate_uuid())  # type: ignore[call-arg]
