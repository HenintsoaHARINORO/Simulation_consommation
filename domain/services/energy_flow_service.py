"""
Service domaine : simulation temporelle des flux énergétiques.
Cœur du moteur – logique physique pure, pas d'I/O.
"""
import numpy as np
import pandas as pd
from domain.entities.installation import BatteryConfig
from domain.entities.results import EnergyKPIs


class EnergyFlowService:
    """
    Simule heure par heure les flux entre production, consommation,
    batterie et réseau.

    Logique à chaque pas t :
    ───────────────────────
    1. self_consumed(t) = min(P(t), C(t))
    2. surplus(t)       = max(0, P(t) – C(t))
    3. déficit(t)       = max(0, C(t) – P(t))

    Avec batterie :
    4. Surplus  → charge la batterie (limites SoC + C-rate)
       Reste    → injection réseau
    5. Déficit  → décharge batterie
       Reste    → soutirage réseau
    """

    def simulate(
        self,
        production: pd.Series,
        consumption: pd.Series,
        battery: BatteryConfig,
    ) -> pd.DataFrame:
        """
        Parameters
        ----------
        production  : pd.Series  [kWh/h], index DatetimeTZ UTC
        consumption : pd.Series  [kWh/h], index DatetimeTZ UTC
        battery     : BatteryConfig

        Returns
        -------
        pd.DataFrame avec colonnes :
            production_kwh, consumption_kwh, self_consumed_kwh,
            injected_kwh, from_grid_kwh,
            bat_charged_kwh, bat_discharged_kwh, battery_soc_kwh
        """
        df = pd.DataFrame({
            "production_kwh":  production,
            "consumption_kwh": consumption,
        }).dropna()

        n = len(df)
        self_consumed  = np.zeros(n)
        injected       = np.zeros(n)
        from_grid      = np.zeros(n)
        bat_charged    = np.zeros(n)
        bat_discharged = np.zeros(n)
        soc_arr        = np.zeros(n)

        prod_arr  = df["production_kwh"].values
        conso_arr = df["consumption_kwh"].values

        cap          = battery.capacity_kwh
        soc_current  = cap * 0.50          # départ à 50 %
        max_kwh      = battery.max_kwh
        min_kwh      = battery.min_kwh
        max_charge   = cap * battery.max_charge_rate_c
        max_discharge = cap * battery.max_discharge_rate_c
        η_ch  = battery.charge_efficiency
        η_dch = battery.discharge_efficiency

        for i in range(n):
            p = prod_arr[i]
            c = conso_arr[i]

            surplus = max(0.0, p - c)
            deficit = max(0.0, c - p)
            self_consumed[i] = min(p, c)

            if battery.has_battery:
                if surplus > 0:
                    room = max_kwh - soc_current
                    stored = min(surplus * η_ch, room, max_charge)
                    bat_charged[i] = stored
                    soc_current   += stored
                    injected[i]    = surplus - stored / η_ch   # énergie non stockée

                elif deficit > 0:
                    available   = soc_current - min_kwh
                    released    = min(deficit / η_dch, available, max_discharge)
                    output      = released * η_dch
                    bat_discharged[i] = output
                    soc_current      -= released
                    from_grid[i]      = max(0.0, deficit - output)
            else:
                injected[i]  = surplus
                from_grid[i] = deficit

            soc_arr[i] = soc_current

        df = df.copy()
        df["self_consumed_kwh"]  = self_consumed
        df["injected_kwh"]       = injected
        df["from_grid_kwh"]      = from_grid
        df["bat_charged_kwh"]    = bat_charged
        df["bat_discharged_kwh"] = bat_discharged
        df["battery_soc_kwh"]    = soc_arr
        return df

    def compute_kpis(self, flows: pd.DataFrame) -> EnergyKPIs:
        """Agrège les flux horaires en KPI annuels."""
        return EnergyKPIs(
            production_kwh    = round(flows["production_kwh"].sum(), 1),
            consumption_kwh   = round(flows["consumption_kwh"].sum(), 1),
            self_consumed_kwh = round(flows["self_consumed_kwh"].sum(), 1),
            injected_kwh      = round(flows["injected_kwh"].sum(), 1),
            from_grid_kwh     = round(flows["from_grid_kwh"].sum(), 1),
        )
