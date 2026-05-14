"""
Interface CLI – Point d'entrée de l'application.

Branche les adaptateurs infrastructure sur les use cases applicatifs.
C'est la seule couche qui connaît à la fois le domaine ET l'infrastructure.
"""
import sys
from pathlib import Path

# Résolution des imports relatifs depuis la racine du projet
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from domain.entities.installation import SystemConfig, BatteryConfig, FinancialConfig
from infrastructure.adapters.synthetic_adapters import (
    SyntheticIrradianceAdapter,
    SyntheticConsumptionAdapter,
)
from domain.services.simulate_installation import SimulateInstallationUseCase
from application.use_cases.optimize_power import OptimizePowerUseCase
from application.dtos.simulation_dto import (
    SimulationRequest, OptimizationRequest,
)


def run_demo():
    print("=" * 60)
    print("   MOTEUR PV GROOWING – Architecture Hexagonale")
    print("=" * 60)

    # ── Configuration ────────────────────────────────────────────
    fin_cfg  = FinancialConfig()
    bat_none = BatteryConfig(capacity_kwh=0)
    bat_6kwh = BatteryConfig(capacity_kwh=6.0)

    # ── Adaptateurs (échangeables sans toucher au domaine) ───────
    irradiance_repo  = SyntheticIrradianceAdapter(year=2023)
    consumption_repo = SyntheticConsumptionAdapter(year=2023)

    # ── Scénarios ────────────────────────────────────────────────
    scenarios = [
        ("Sans batterie",       SystemConfig(peak_power_kwp=6.0), bat_none),
        ("Avec batterie 6 kWh", SystemConfig(peak_power_kwp=6.0), bat_6kwh),
    ]

    for label, sys_cfg, bat_cfg in scenarios:
        request = SimulationRequest(
            sys_config        = sys_cfg,
            bat_config        = bat_cfg,
            fin_config        = fin_cfg,
            label             = label,
            target_annual_kwh = 3500.0,
        )
        use_case = SimulateInstallationUseCase(irradiance_repo, consumption_repo)
        result   = use_case.execute(request)
        print(result.summary())

        # Extrait des 4 premières heures de midi
        sample = result.hourly_flows.between_time("12:00", "15:00").head(4)
        print("\n  Extrait flux horaires (12h–15h) :")
        print(
            sample[["production_kwh", "consumption_kwh",
                     "self_consumed_kwh", "injected_kwh",
                     "from_grid_kwh"]].round(3).to_string()
        )

    # ── Optimisation de puissance ─────────────────────────────────
    print(f"\n{'='*60}")
    print("  OPTIMISATION DE LA PUISSANCE (sans batterie)")
    print(f"{'='*60}")

    opt_request = OptimizationRequest(
        bat_config        = bat_none,
        fin_config        = fin_cfg,
        power_min_kwp     = 1.0,
        power_max_kwp     = 12.0,
        power_step_kwp    = 1.0,
        max_roof_area_m2  = 40.0,
        target_annual_kwh = 3500.0,
    )

    opt_use_case = OptimizePowerUseCase(irradiance_repo, consumption_repo)
    opt_result   = opt_use_case.execute(opt_request)

    cols = ["puissance_kwp", "taux_autoconsommation_pct",
            "taux_autosuffisance_pct", "VAN_EUR", "TRI_pct",
            "payback_years", "optimal"]
    print(opt_result.sweep_results[cols].to_string(index=False))

    best = opt_result.optimal_result
    print(
        f"\n→ Puissance optimale : {opt_result.optimal_power_kwp} kWc\n"
        f"{best.financial_kpis}"
    )


if __name__ == "__main__":
    run_demo()
