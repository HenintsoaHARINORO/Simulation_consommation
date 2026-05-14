"""
Adaptateurs de données synthétiques (développement / tests / démo).
Permet de faire tourner le moteur sans fichiers réels.
"""
import numpy as np
import pandas as pd
from typing import Optional

from domain.ports.repositories import IrradianceRepository, ConsumptionRepository


class SyntheticIrradianceAdapter(IrradianceRepository):
    """
    Génère une irradiance annuelle synthétique typique France méditerranéenne.
    Production normalisée ≈ 1 400 kWh/kWc/an (Montpellier).
    """

    ANNUAL_YIELD_KWH_PER_KWP = 1400.0

    def __init__(self, year: int = 2023, seed: int = 0):
        self._year = year
        self._seed = seed

    def load(self) -> pd.Series:
        idx = pd.date_range(
            f"{self._year}-01-01",
            f"{self._year}-12-31 23:00",
            freq="h",
            tz="UTC",
        )
        rng = np.random.default_rng(self._seed)

        # Angle solaire simplifié : sinusoïde journalière + saisonnalité
        hour_of_year = np.arange(len(idx))
        day_angle    = (hour_of_year % 24 - 12) / 12 * np.pi
        season_angle = (idx.dayofyear / 365) * 2 * np.pi

        irr = np.maximum(
            0,
            np.sin(day_angle) * (0.6 + 0.4 * np.cos(season_angle - np.pi / 2))
        )
        noise = rng.normal(1, 0.03, size=len(idx))
        irr   = np.maximum(0, irr * noise)

        # Normalisation à 1 400 kWh/kWc/an
        irr_series = pd.Series(irr, index=idx)
        irr_series = irr_series / irr_series.sum() * self.ANNUAL_YIELD_KWH_PER_KWP

        return irr_series.rename("irradiance_kwh_per_kwp")


class SyntheticConsumptionAdapter(ConsumptionRepository):
    """
    Génère un profil de consommation résidentiel synthétique.
    Profil type INSEE/RTE : double pic matin/soir, saisonnalité hivernale.
    """

    # Profil horaire normalisé (0 à 23h)
    HOURLY_PROFILE = np.array([
        0.30, 0.25, 0.22, 0.20, 0.20, 0.28,   # 0–5h  (nuit)
        0.45, 0.75, 0.90, 0.80, 0.65, 0.60,   # 6–11h (matin)
        0.65, 0.60, 0.55, 0.55, 0.60, 0.75,   # 12–17h (journée)
        1.00, 1.00, 0.95, 0.80, 0.60, 0.40,   # 18–23h (soir)
    ])

    def __init__(self, year: int = 2023, seed: int = 42):
        self._year = year
        self._seed = seed

    def load(self, target_annual_kwh: Optional[float] = None) -> pd.Series:
        annual = target_annual_kwh or 3500.0

        idx = pd.date_range(
            f"{self._year}-01-01",
            f"{self._year}-12-31 23:00",
            freq="h",
            tz="UTC",
        )
        rng     = np.random.default_rng(self._seed)
        hours   = np.array(idx.hour)
        months  = np.array(idx.month)

        seasonal = 1.0 + 0.15 * np.cos((months - 1) * 2 * np.pi / 12)
        base     = self.HOURLY_PROFILE[hours] * seasonal
        noise    = rng.normal(1, 0.05, size=len(idx))
        conso    = np.maximum(0, base * noise)

        conso_series = pd.Series(conso, index=idx)
        conso_series = conso_series / conso_series.sum() * annual

        return conso_series.rename("consumption_kwh")
