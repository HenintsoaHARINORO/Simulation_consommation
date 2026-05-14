"""
Use case : simuler une installation photovoltaïque.
Orchestre les services domaine et les repositories (ports).
"""
from domain.ports.repositories import IrradianceRepository, ConsumptionRepository
from domain.services.production_service import ProductionService
from domain.services.energy_flow_service import EnergyFlowService
from domain.services.financial_service import FinancialService
from application.dtos.simulation_dto import SimulationRequest, SimulationResult


class SimulateInstallationUseCase:
    """
    Orchestre une simulation complète :
      1. Charge l'irradiance (port)
      2. Charge la consommation (port)
      3. Calcule la production (service domaine)
      4. Simule les flux énergétiques (service domaine)
      5. Calcule les indicateurs financiers (service domaine)
    """

    def __init__(
        self,
        irradiance_repo:  IrradianceRepository,
        consumption_repo: ConsumptionRepository,
        production_svc:   ProductionService   | None = None,
        flow_svc:         EnergyFlowService   | None = None,
        financial_svc:    FinancialService    | None = None,
    ):
        self._irradiance_repo  = irradiance_repo
        self._consumption_repo = consumption_repo
        # Injection de dépendance (valeurs par défaut pour faciliter l'usage)
        self._production_svc   = production_svc  or ProductionService()
        self._flow_svc         = flow_svc        or EnergyFlowService()
        self._financial_svc    = financial_svc   or FinancialService()

    def execute(self, request: SimulationRequest) -> SimulationResult:
        # 1. Données sources
        irradiance_1kwp = self._irradiance_repo.load()
        consumption     = self._consumption_repo.load(request.target_annual_kwh)

        # 2. Production selon la configuration
        production = self._production_svc.compute(irradiance_1kwp, request.sys_config)

        # 3. Simulation temporelle des flux
        hourly_flows = self._flow_svc.simulate(production, consumption, request.bat_config)
        energy_kpis  = self._flow_svc.compute_kpis(hourly_flows)

        # 4. Projection financière
        cashflows      = self._financial_svc.compute_cashflows(
            energy_kpis, request.sys_config, request.bat_config, request.fin_config
        )
        financial_kpis = self._financial_svc.compute_financial_kpis(
            cashflows, request.sys_config, request.bat_config, request.fin_config
        )

        return SimulationResult(
            label          = request.label,
            sys_config     = request.sys_config,
            bat_config     = request.bat_config,
            energy_kpis    = energy_kpis,
            financial_kpis = financial_kpis,
            cashflows      = cashflows,
            hourly_flows   = hourly_flows,
        )
