"""
Adaptateur infrastructure : chargement des données PVGIS (CSV horaire).
Implémente le port IrradianceRepository.
"""
import pandas as pd
from domain.ports.repositories import IrradianceRepository


class PvgisIrradianceAdapter(IrradianceRepository):
    """
    Lit un fichier CSV exporté depuis PVGIS (API ou interface web).

    Format attendu (PVGIS Hourly Data) :
      – Lignes de métadonnées ignorées (skiprows=8)
      – Colonnes : time, G(i), Gb(i), Gd(i), Gr(i), H_sun, T2m, WS10m, Int
      – time au format YYYYMMDD:HHMM (ex: 20230115:1300)

    La série retournée est normalisée sur 1 kWc :
        kWh/kWc = G(i) [W/m²] / 1000 × PR_corr
    (PR_corr = 1 ici car le PR est appliqué dans ProductionService)
    """

    COLUMNS = ["time", "ghi_wm2", "gb_wm2", "gd_wm2",
               "gr_wm2", "h_sun", "T2m", "WS10m", "Int"]

    def __init__(self, filepath: str):
        self._filepath = filepath

    def load(self) -> pd.Series:
        df = pd.read_csv(
            self._filepath,
            skiprows=8,
            skipfooter=12,
            engine="python",
            names=self.COLUMNS,
        )
        df["time"] = pd.to_datetime(df["time"], format="%Y%m%d:%H%M", utc=True)
        df = df.set_index("time")[["ghi_wm2"]].astype(float)

        # Conversion W/m² → kWh/kWc (hypothèse : surface 1 m² pour 1 kWc à η=1)
        irradiance_1kwp = (df["ghi_wm2"] / 1000.0).clip(lower=0)
        return irradiance_1kwp.rename("irradiance_kwh_per_kwp")
