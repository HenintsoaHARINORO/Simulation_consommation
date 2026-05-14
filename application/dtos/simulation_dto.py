"""
DTO (Data Transfer Objects) – objets de communication entre
la couche application et les interfaces (CLI, API…).
"""
from dataclasses import dataclass, field
from typing import Optional
import pandas as pd

from domain.entities.installation import SystemConfig, BatteryConfig, FinancialConfig
from domain.entities.results import EnergyKPIs, FinancialKPIs


@dataclass
class SimulationRequest:
    """Paramètres d'entrée d'une simulation."""
    sys_config:  SystemConfig
    bat_config:  BatteryConfig
    fin_config:  FinancialConfig
    label:       str = "Simulation"
    # Source des données (l'application injecte les repositories)
    target_annual_kwh: Optional[float] = None


@dataclass
class SimulationResult:
    """Résultat complet d'une simulation."""
    label:          str
    sys_config:     SystemConfig
    bat_config:     BatteryConfig
    energy_kpis:    EnergyKPIs
    financial_kpis: FinancialKPIs
    cashflows:      pd.DataFrame
    hourly_flows:   pd.DataFrame

    def summary(self) -> str:
        return (
            f"\n{'─'*50}\n"
            f"  {self.label} | {self.sys_config.peak_power_kwp} kWc"
            + (f" + {self.bat_config.capacity_kwh} kWh" if self.bat_config.has_battery else "")
            + f"\n{'─'*50}\n"
            f"{self.energy_kpis}\n\n"
            f"{self.financial_kpis}"
        )


@dataclass
class OptimizationRequest:
    """Paramètres d'une recherche de puissance optimale."""
    bat_config:        BatteryConfig
    fin_config:        FinancialConfig
    power_min_kwp:     float = 1.0
    power_max_kwp:     float = 36.0
    power_step_kwp:    float = 0.5
    max_roof_area_m2:  Optional[float] = None
    panel_area_m2:     float = 1.7
    panel_power_kwp:   float = 0.40   # kWc/panneau
    target_annual_kwh: Optional[float] = None


@dataclass
class OptimizationResult:
    """Résultat de l'optimisation de puissance."""
    sweep_results:     pd.DataFrame   # tous les scénarios testés
    optimal_power_kwp: float
    optimal_result:    SimulationResult
