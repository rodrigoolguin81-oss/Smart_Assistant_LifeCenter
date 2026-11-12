"""`Fragment` entity: one retrievable section of a knowledge base document. Pure — no I/O."""

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Fragment:
    text: str
    titulo: str
    source_id: str
    tipo: str
    vigente_desde: date
    ejemplo: bool
    score: float | None = None

    @property
    def cita(self) -> str:
        """Source citation required in every grounded answer (R6)."""
        return f"[{self.source_id} | vigente desde {self.vigente_desde:%d/%m/%Y}]"
