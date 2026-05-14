"""
Adaptateur infrastructure : courbe de charge Enedis (CSV 30 min).
Implémente le port ConsumptionRepository.
"""
import pandas as pd
from typing import Optional
from domain.ports.repositories import ConsumptionRepository


class EnedisConsumptionAdapter(ConsumptionRepository):
    """
    Lit un fichier CSV Enedis (export courbe de charge, pas 30 min).

    Format attendu :
      – Séparateur ";"
      – Colonnes : Horodatage, Valeur (en W ou kWh selon compteur)
      – Dates au format DD/MM/YYYY HH:MM

    Traitement :
      1. Détection automatique de l'unité (W → kWh = valeur × 0.5 / 1000)
      2. Ré-échantillonnage 30 min → 1h par sommation
      3. Normalisation optionnelle sur consommation annuelle cible
    """

    def __init__(self, filepath: str):
        self._filepath = filepath

    def load(self, target_annual_kwh: Optional[float] = None) -> pd.Series:
        df = pd.read_csv(
            self._filepath,
            sep=";",
            parse_dates=["Horodatage"],
            dayfirst=True,
            decimal=",",
        )
        df = (
            df.rename(columns={"Horodatage": "time", "Valeur": "conso"})
              .set_index("time")
              .sort_index()
        )

        # Conversion W → kWh si nécessaire (heuristique : moyenne > 5)
        if df["conso"].mean() > 5:
            df["conso"] = df["conso"] * 0.5 / 1000  # W × 0.5h / 1000

        # Ré-échantillonnage horaire
        hourly = df["conso"].resample("h").sum().rename("consumption_kwh")

        if target_annual_kwh:
            hourly = hourly * (target_annual_kwh / hourly.sum())

        return hourly.clip(lower=0)
