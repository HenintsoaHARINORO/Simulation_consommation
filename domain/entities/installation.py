"""
Entités métier : représentent les objets centraux du domaine PV.
Aucune dépendance externe – zéro import infrastructure.
"""
from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class SystemConfig:
    """Configuration physique de l'installation photovoltaïque."""
    peak_power_kwp: float           # Puissance crête (kWc)
    pr: float = 0.80                # Performance Ratio global
    panel_efficiency: float = 0.20  # Rendement panneau
    orientation: float = 180.0      # Azimut (180 = plein sud)
    tilt: float = 35.0              # Inclinaison (°)

    def __post_init__(self):
        if self.peak_power_kwp <= 0:
            raise ValueError("La puissance crête doit être > 0")
        if not 0 < self.pr <= 1:
            raise ValueError("Le Performance Ratio doit être entre 0 et 1")


@dataclass(frozen=True)
class BatteryConfig:
    """Configuration du système de stockage (batterie physique)."""
    capacity_kwh: float = 0.0           # 0 = pas de batterie
    charge_efficiency: float = 0.95
    discharge_efficiency: float = 0.95
    max_soc: float = 0.90               # SoC maximum autorisé
    min_soc: float = 0.10               # SoC minimum autorisé
    max_charge_rate_c: float = 1.0      # C-rate max charge
    max_discharge_rate_c: float = 1.0   # C-rate max décharge

    @property
    def has_battery(self) -> bool:
        return self.capacity_kwh > 0

    @property
    def max_kwh(self) -> float:
        return self.capacity_kwh * self.max_soc

    @property
    def min_kwh(self) -> float:
        return self.capacity_kwh * self.min_soc


@dataclass(frozen=True)
class FinancialConfig:
    """Paramètres économiques, réglementaires et de financement."""
    # Coûts
    capex_per_kwp: float = 1400.0
    opex_annual_eur: float = 150.0
    battery_cost_per_kwh: float = 600.0

    # Prix énergie
    grid_price_eur_kwh: float = 0.2276
    sell_price_eur_kwh: float = 0.1276

    # Prime autoconsommation (€/kWc/an, selon paliers réglementaires)
    autoconso_premium_schedule: dict = field(default_factory=lambda: {
        3:   200,
        9:   200,
        36:  120,
        100:  60,
        500:  60,
    })
    premium_duration_years: int = 20

    # Financement
    loan_rate: float = 0.04
    loan_duration_years: int = 10
    equity_fraction: float = 0.20

    # Projection
    elec_price_inflation: float = 0.04
    sell_price_inflation: float = 0.01
    panel_degradation_annual: float = 0.005
    project_life_years: int = 25
    discount_rate: float = 0.05
