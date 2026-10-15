from dataclasses import dataclass


@dataclass(frozen=True)
class Position:
    row: int
    column: int

    def __post_init__(self):
        if type(self.row) is not int or self.row < 0:
            raise ValueError("La fila debe ser un entero no negativo.")

        if type(self.column) is not int or self.column < 0:
            raise ValueError("La columna debe ser un entero no negativo.")
