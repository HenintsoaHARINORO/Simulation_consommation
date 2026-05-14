"""
Ports du domaine (interfaces abstraites).

Un port = un contrat que l'infrastructure doit implémenter.
Le domaine ne sait JAMAIS d'où viennent les données.
"""
from abc import ABC, abstractmethod
import pandas as pd


class IrradianceRepository(ABC):
    """Port primaire : fournit les données d'irradiance horaires."""

    @abstractmethod
    def load(self) -> pd.Series:
        """
        Retourne une Series horaire (kWh/kWc) indexée en DatetimeTZDtype UTC.
        La normalisation sur 1 kWc est déjà appliquée.
        """
        ...


class ConsumptionRepository(ABC):
    """Port primaire : fournit la courbe de charge horaire."""

    @abstractmethod
    def load(self, target_annual_kwh: float | None = None) -> pd.Series:
        """
        Retourne une Series horaire (kWh) indexée en DatetimeTZDtype UTC.
        Si target_annual_kwh est fourni, normalise le profil.
        """
        ...


class SimulationResultRepository(ABC):
    """Port secondaire : persiste les résultats de simulation."""

    @abstractmethod
    def save(self, label: str, flows: pd.DataFrame) -> None:
        """Sauvegarde le DataFrame des flux énergétiques horuaires."""
        ...
