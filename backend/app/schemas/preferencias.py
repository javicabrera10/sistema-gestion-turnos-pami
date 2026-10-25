from typing import Literal

from pydantic import BaseModel, ConfigDict, StrictBool


class PreferenciasSchema(BaseModel):
    """Preferencias de accesibilidad de un usuario. Solo entran valores permitidos."""

    model_config = ConfigDict(extra="forbid")

    tamano_letra: Literal["normal", "grande", "muy_grande"]
    alto_contraste: StrictBool
    voz_activada: StrictBool