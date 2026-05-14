"""
Service domaine : moteur financier.
Calcule les cash-flows, VAN, TRI et le retour sur investissement.
"""
import numpy as np
import pandas as pd
from typing import Optional

from domain.entities.installation import SystemConfig, BatteryConfig, FinancialConfig
from domain.entities.results import EnergyKPIs, FinancialKPIs


class FinancialService:
    """
    Projette la rentabilité d'une installation sur sa durée de vie.

    Revenus annuels :
      • Économies achat réseau  = E_auto × prix_achat × (1+inflation)^t
      • Vente surplus           = E_inject × prix_vente × (1+inflation_vente)^t
      • Prime autoconsommation  = P_kWc × prime_kWc  (20 ans, décret)

    Charges :
      • OPEX (maintenance + assurance) indexé +2%/an
      • Annuités crédit (durée configurable)
    """

    def get_autoconso_premium(
        self,
        peak_power_kwp: float,
        schedule: dict,
    ) -> float:
        """Prime autoconsommation (€/kWc/an) selon grille réglementaire."""
        for threshold, premium in sorted(schedule.items()):
            if peak_power_kwp <= threshold:
                return premium
        return list(schedule.values())[-1]

    def _loan_annuity(
        self,
        principal: float,
        rate: float,
        duration: int,
    ) -> float:
        """Annuité constante de remboursement crédit."""
        if rate == 0 or principal == 0:
            return principal / duration if duration else 0
        return principal * rate / (1 - (1 + rate) ** -duration)

    def compute_cashflows(
        self,
        energy_kpis: EnergyKPIs,
        sys_config: SystemConfig,
        bat_config: BatteryConfig,
        fin: FinancialConfig,
    ) -> pd.DataFrame:
        """Retourne un DataFrame des cash-flows annuels (année 0 = investissement)."""
        capex = (
            sys_config.peak_power_kwp * fin.capex_per_kwp
            + bat_config.capacity_kwh * fin.battery_cost_per_kwh
        )
        equity     = capex * fin.equity_fraction
        loan       = capex * (1 - fin.equity_fraction)
        annuity    = self._loan_annuity(loan, fin.loan_rate, fin.loan_duration_years)
        premium_yr = self.get_autoconso_premium(
            sys_config.peak_power_kwp,
            fin.autoconso_premium_schedule,
        )

        rows = [{
            "annee":           0,
            "economies_elec":  0.0,
            "revenus_vente":   0.0,
            "prime_autoconso": 0.0,
            "opex":            0.0,
            "annuite_credit":  0.0,
            "cashflow_net":    -equity,
            "cashflow_cumule": -equity,
        }]

        cumul = -equity
        for yr in range(1, fin.project_life_years + 1):
            degr      = (1 - fin.panel_degradation_annual) ** (yr - 1)
            elec_inf  = (1 + fin.elec_price_inflation)  ** (yr - 1)
            sell_inf  = (1 + fin.sell_price_inflation)   ** (yr - 1)

            eco    = energy_kpis.self_consumed_kwh * degr * fin.grid_price_eur_kwh * elec_inf
            vente  = energy_kpis.injected_kwh      * degr * fin.sell_price_eur_kwh * sell_inf
            prime  = sys_config.peak_power_kwp * premium_yr if yr <= fin.premium_duration_years else 0
            opex   = fin.opex_annual_eur * (1.02 ** (yr - 1))
            annuit = annuity if yr <= fin.loan_duration_years else 0

            cf  = eco + vente + prime - opex - annuit
            cumul += cf

            rows.append({
                "annee":           yr,
                "economies_elec":  round(eco,   2),
                "revenus_vente":   round(vente, 2),
                "prime_autoconso": round(prime, 2),
                "opex":            round(-opex,   2),
                "annuite_credit":  round(-annuit, 2),
                "cashflow_net":    round(cf,    2),
                "cashflow_cumule": round(cumul, 2),
            })

        return pd.DataFrame(rows)

    def compute_financial_kpis(
        self,
        cashflows: pd.DataFrame,
        sys_config: SystemConfig,
        bat_config: BatteryConfig,
        fin: FinancialConfig,
    ) -> FinancialKPIs:
        """Calcule VAN, TRI et payback à partir des cash-flows."""
        cf      = cashflows["cashflow_net"].values
        periods = np.arange(len(cf))

        # ── VAN ──
        npv = float(np.sum(cf / (1 + fin.discount_rate) ** periods))

        # ── TRI  (Newton-Raphson) ──
        irr = self._compute_irr(cf, periods)

        # ── Payback ──
        payback: Optional[int] = None
        for i, c in enumerate(cashflows["cashflow_cumule"].values):
            if c >= 0:
                payback = int(i)
                break

        capex = (
            sys_config.peak_power_kwp * fin.capex_per_kwp
            + bat_config.capacity_kwh * fin.battery_cost_per_kwh
        )

        return FinancialKPIs(
            npv_eur        = round(npv, 0),
            irr_pct        = round(irr * 100, 2) if irr is not None else None,
            payback_years  = payback,
            total_capex_eur= round(capex, 0),
        )

    @staticmethod
    def _compute_irr(cf: np.ndarray, periods: np.ndarray) -> Optional[float]:
        """Newton-Raphson pour le calcul du TRI."""
        guess = 0.08
        try:
            for _ in range(1000):
                f   = np.sum(cf / (1 + guess) ** periods)
                df_ = np.sum(-periods * cf / (1 + guess) ** (periods + 1))
                if abs(df_) < 1e-12:
                    break
                new = guess - f / df_
                if abs(new - guess) < 1e-8:
                    return new
                guess = new
            return guess
        except Exception:
            return None
