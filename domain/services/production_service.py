"""
Service domaine : calcul de la production photovoltaïque.
Physique pure – aucune dépendance infrastructure.
"""
import pandas as pd
from domain.entities.installation import SystemConfig


class ProductionService:
    """
    Calcule la production horaire à partir de l'irradiance plane du capteur.

    Formule :
        P(t) [kWh] = GHI(t) [kWh/kWc] × peak_power [kWc] × PR

    L'irradiance d'entrée est déjà sur le plan incliné (PVGIS l'applique),
    normalisée à 1 kWc. Le PR englobe les pertes câblage, onduleur,
    température et encrassement.
    """

    def compute(
        self,
        irradiance_1kwp: pd.Series,
        config: SystemConfig,
    ) -> pd.Series:
        """
        Parameters
        ----------
        irradiance_1kwp : pd.Series
            Irradiance horaire normalisée (kWh/kWc), index DatetimeTZ UTC.
        config : SystemConfig
            Configuration de l'installation.

        Returns
        -------
        pd.Series
            Production horaire (kWh), même index que l'entrée.
        """
        production = (
            irradiance_1kwp
            * config.peak_power_kwp
            * config.pr
        ).clip(lower=0)

        return production.rename("production_kwh")
