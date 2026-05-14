"""
Value objects immuables représentant les résultats de simulation.
"""
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class EnergyKPIs:
    """KPI énergétiques annuels d'une simulation."""
    production_kwh: float
    consumption_kwh: float
    self_consumed_kwh: float
    injected_kwh: float
    from_grid_kwh: float

    @property
    def self_consumption_rate(self) -> float:
        """Taux d'autoconsommation : part de la prod autoconsommée."""
        return self.self_consumed_kwh / self.production_kwh if self.production_kwh else 0

    @property
    def self_sufficiency_rate(self) -> float:
        """Taux d'autosuffisance : part de la conso couverte par le PV."""
        return self.self_consumed_kwh / self.consumption_kwh if self.consumption_kwh else 0

    def __str__(self) -> str:
        return (
            f"Production       : {self.production_kwh:>8.1f} kWh/an\n"
            f"Consommation     : {self.consumption_kwh:>8.1f} kWh/an\n"
            f"Autoconsommée    : {self.self_consumed_kwh:>8.1f} kWh/an\n"
            f"Injectée réseau  : {self.injected_kwh:>8.1f} kWh/an\n"
            f"Soutirage réseau : {self.from_grid_kwh:>8.1f} kWh/an\n"
            f"Taux autoconso   : {self.self_consumption_rate * 100:>7.1f} %\n"
            f"Autosuffisance   : {self.self_sufficiency_rate * 100:>7.1f} %"
        )


@dataclass(frozen=True)
class FinancialKPIs:
    """Indicateurs financiers d'un projet PV sur sa durée de vie."""
    npv_eur: float                   # Valeur Actuelle Nette
    irr_pct: Optional[float]         # Taux de Rendement Interne (%)
    payback_years: Optional[int]     # Retour sur investissement (années)
    total_capex_eur: float           # Investissement total (€)

    def __str__(self) -> str:
        irr_str = f"{self.irr_pct:.1f} %" if self.irr_pct else "N/A"
        pb_str  = f"{self.payback_years} ans" if self.payback_years else "N/A"
        return (
            f"Investissement   : {self.total_capex_eur:>8,.0f} €\n"
            f"VAN              : {self.npv_eur:>8,.0f} €\n"
            f"TRI              : {irr_str:>10}\n"
            f"Retour invest.   : {pb_str:>10}"
        )
