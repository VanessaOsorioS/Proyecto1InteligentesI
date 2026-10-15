from dataclasses import dataclass

@dataclass(frozen=True)
class Terrain:

    name: str
    walkable: bool
    cost: float | None = None

    def __post_init__(self):
        if not isinstance(self.name, str) or not self.name:
            raise ValueError("El terreno necesita un nombre válido.")

        if type(self.walkable) is not bool:
            raise ValueError("'walkable' debe ser booleano.")

        if self.walkable:
            if (
                type(self.cost) not in (int, float)
                or self.cost <= 0
            ):
                raise ValueError(
                    "Un terreno transitable debe tener un costo positivo."
                )
        elif self.cost is not None:
            raise ValueError(
                "Un terreno no transitable no debe tener costo."
            )
