"""
Use case : optimisation de la puissance installée.
Balayage de puissance → maximisation de la VAN.
"""
import numpy as np
import pandas as pd
from typing import Optional

from domain.entities.installation import SystemConfig
from domain.ports.repositories import IrradianceRepository, ConsumptionRepository
from domain.services.production_service import ProductionService
from domain.services.energy_flow_service import EnergyFlowService
from domain.services.financial_service import FinancialService
from application.dtos.simulation_dto import (
    OptimizationRequest, OptimizationResult,
    SimulationRequest, SimulationResult,
)
from domain.services.simulate_installation import SimulateInstallationUseCase


class OptimizePowerUseCase:
    """
    Détermine la puissance crête optimale d'une installation.

    Algorithme :
    ─────────────
    Pour chaque puissance P dans [P_min … P_max] (pas configurable) :
      1. Instancier un SystemConfig avec cette puissance
      2. Déléguer à SimulateInstallationUseCase
      3. Stocker VAN, TRI, payback, taux autoconso, autosuffisance
    Retourne le scénario qui maximise la VAN.

    Contraintes supportées :
      – Surface toiture max (m²) → P_max_surface
      – Puissance max réseau (imposée en paramètre)
    """

    def __init__(
        self,
        irradiance_repo:  IrradianceRepository,
        consumption_repo: ConsumptionRepository,
    ):
        self._irradiance_repo  = irradiance_repo
        self._consumption_repo = consumption_repo
        self._production_svc   = ProductionService()
        self._flow_svc         = EnergyFlowService()
        self._financial_svc    = FinancialService()

    def execute(self, request: OptimizationRequest) -> OptimizationResult:
        # Contrainte surface toiture
        p_max = request.power_max_kwp
        if request.max_roof_area_m2:
            max_panels    = int(request.max_roof_area_m2 / request.panel_area_m2)
            p_max_surface = max_panels * request.panel_power_kwp
            p_max         = min(p_max, p_max_surface)

        powers = np.arange(
            request.power_min_kwp,
            p_max + request.power_step_kwp,
            request.power_step_kwp,
        )

        rows: list[dict] = []
        results: dict[float, SimulationResult] = {}

        for p in powers:
            sys_cfg = SystemConfig(peak_power_kwp=float(round(p, 2)))
            sim_req = SimulationRequest(
                sys_config        = sys_cfg,
                bat_config        = request.bat_config,
                fin_config        = request.fin_config,
                label             = f"{p:.1f} kWc",
                target_annual_kwh = request.target_annual_kwh,
            )
            use_case = SimulateInstallationUseCase(
                irradiance_repo  = self._irradiance_repo,
                consumption_repo = self._consumption_repo,
                production_svc   = self._production_svc,
                flow_svc         = self._flow_svc,
                financial_svc    = self._financial_svc,
            )
            result = use_case.execute(sim_req)
            results[float(round(p, 2))] = result

            rows.append({
                "puissance_kwp":              round(p, 2),
                "taux_autoconsommation_pct":  round(result.energy_kpis.self_consumption_rate * 100, 1),
                "taux_autosuffisance_pct":    round(result.energy_kpis.self_sufficiency_rate  * 100, 1),
                "production_kwh":             result.energy_kpis.production_kwh,
                "VAN_EUR":                    result.financial_kpis.npv_eur,
                "TRI_pct":                    result.financial_kpis.irr_pct,
                "payback_years":              result.financial_kpis.payback_years,
                "capex_eur":                  result.financial_kpis.total_capex_eur,
            })

        sweep_df = pd.DataFrame(rows)
        best_idx  = sweep_df["VAN_EUR"].idxmax()
        best_p    = float(sweep_df.loc[best_idx, "puissance_kwp"])

        sweep_df["optimal"] = sweep_df["puissance_kwp"] == best_p

        return OptimizationResult(
            sweep_results     = sweep_df,
            optimal_power_kwp = best_p,
            optimal_result    = results[best_p],
        )
