# Moteur PV

Moteur de **simulation photovoltaïque** bâti sur une **architecture hexagonale** (Ports & Adapters). Le domaine métier est totalement découplé de l'infrastructure (CSV Enedis, PVGIS, données synthétiques) et de l'interface (CLI, Streamlit).

> Pour les réponses au questionnaire de sélection, voir [responses.md](./responses.md).

---

## Apercu

**Panneau de configuration**

![Sidebar](./screenshots/sidebar.png)

**Flux energetiques mensuels**

![Plot](./screenshots/plot.png)

---

## Structure du projet

```
.
├── domain/                        # Coeur metier – zero dependance externe
│   ├── entities/
│   │   ├── installation.py        # SystemConfig, BatteryConfig, FinancialConfig
│   │   └── results.py             # EnergyKPIs, FinancialKPIs
│   ├── ports/
│   │   └── repositories.py        # Interfaces IrradianceRepository, ConsumptionRepository
│   └── services/
│       ├── production_service.py  # kWh produits depuis irradiance + config
│       ├── energy_flow_service.py # Flux horaires + gestion batterie
│       ├── financial_service.py   # Cashflows, VAN, TRI, payback
│       └── simulate_installation.py  # Orchestrateur (use case domaine)
│
├── application/                   # Cas d'usage applicatifs
│   ├── dtos/simulation_dto.py     # SimulationRequest/Result, OptimizationRequest/Result
│   └── use_cases/optimize_power.py  # Balayage de puissance -> VAN max
│
├── infrastructure/
│   └── adapters/
│       └── synthetic_adapters.py  # Irradiance & consommation synthetiques
│
├── pvgis_irradiance_adapter.py    # Adaptateur CSV PVGIS
├── enedis_consumption_adapter.py  # Adaptateur CSV Enedis (courbe de charge 30 min)
├── csv_result_repository.py       # Export resultats en CSV
│
├── streamlit_app.py               # Interface web (upload CSV + simulation + KPIs)
├── main.py                        # CLI de demonstration
├── responses.md                   # Reponses au questionnaire de selection
│
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

---

## Demarrage rapide

### Prerequis

- Python 3.11+ ou Docker

### Installation locale

```bash
git clone https://github.com/HenintsoaHARINORO/Simulation_consommation
cd Simulation_consommation

python -m venv .venv
source .venv/bin/activate          # Windows : .venv\Scripts\activate

pip install -r requirements.txt
```

### Lancer l'interface web

```bash
streamlit run streamlit_app.py
```

Ouvrez [http://localhost:8501](http://localhost:8501) dans votre navigateur.

### Lancer la demo CLI

```bash
python main.py
```

---

## Docker

```bash
# Build et lancement
docker compose up --build

# Arriere-plan
docker compose up -d

# Logs
docker compose logs -f pv-engine

# Arret
docker compose down
```

L'interface est accessible sur [http://localhost:8501](http://localhost:8501).

---

## Formats de fichiers CSV attendus

### Irradiance – Export PVGIS (Hourly Data)

Telechargeable depuis [https://re.jrc.ec.europa.eu/pvg_tools/](https://re.jrc.ec.europa.eu/pvg_tools/).

| Colonne | Format | Exemple |
|---------|--------|---------|
| `time`  | `YYYYMMDD:HHMM` | `20230615:1300` |
| `G(i)`  | W/m² (float) | `823.4` |
| `Gb(i)` | W/m² | … |
| `Gd(i)` | W/m² | … |

> Le fichier contient 8 lignes de metadonnees en en-tete et 12 lignes de pied de page — elles sont ignorees automatiquement.

### Consommation – Export Enedis (courbe de charge 30 min)

Telechargeable depuis votre espace client [Enedis](https://mon-compte-client.enedis.fr/).

| Colonne | Format | Exemple |
|---------|--------|---------|
| `Horodatage` | `DD/MM/YYYY HH:MM` | `15/06/2023 13:30` |
| `Valeur` | W ou kWh (detection auto) | `1245,5` |

> Separateur `;` · decimale `,`

---

## Architecture hexagonale

```
+-----------------------------------------------------+
|                    INTERFACES                       |
|         Streamlit App          CLI (main.py)        |
+------------------+----------------------------------+
                   | SimulationRequest
+------------------v----------------------------------+
|                 APPLICATION                         |
|   SimulateInstallationUseCase  OptimizePowerUseCase |
+------------------+----------------------------------+
                   | ports (interfaces Python)
+------------------v----------------------------------+
|                   DOMAIN                            |
|  ProductionService · EnergyFlowService              |
|  FinancialService  · entities · KPIs                |
+------------------+----------------------------------+
                   | IrradianceRepository / ConsumptionRepository
+------------------v----------------------------------+
|               INFRASTRUCTURE                        |
|  PvgisIrradianceAdapter   EnedisConsumptionAdapter  |
|  SyntheticIrradianceAdapter  SyntheticConsumption   |
+-----------------------------------------------------+
```

Les adaptateurs infrastructure sont interchangeables sans toucher au domaine metier.

---

## Fonctionnalites de l'interface

| Section | Detail |
|---------|--------|
| Source de donnees | Mode synthetique ou upload CSV (PVGIS + Enedis) |
| Configuration | Puissance crete, consommation annuelle cible |
| KPIs | Production, autoconsommation, autosuffisance, VAN, TRI, payback |
| Semaine type | Flux horaires sur 7 jours (juillet) — production, consommation, autoconsommee, injection, soutirage |
| Vue mensuelle | Barres groupees par mois avec annotation du pic de production |
| Vue annuelle | Production vs consommation hebdomadaire + injection et soutirage en sous-graphe |

---

## Parametres configurables

### SystemConfig

| Parametre | Defaut | Description |
|-----------|--------|-------------|
| `peak_power_kwp` | — | Puissance crete (kWc) |
| `pr` | 0.80 | Performance Ratio |
| `panel_efficiency` | 0.20 | Rendement panneau |
| `orientation` | 180° | Azimut (180 = plein sud) |
| `tilt` | 35° | Inclinaison |

### FinancialConfig

| Parametre | Defaut | Description |
|-----------|--------|-------------|
| `capex_per_kwp` | 1 400 €/kWc | Cout d'installation |
| `grid_price_eur_kwh` | 0,2276 €/kWh | Prix achat reseau |
| `sell_price_eur_kwh` | 0,1276 €/kWh | Tarif revente |
| `discount_rate` | 5 % | Taux d'actualisation (VAN) |
| `project_life_years` | 25 ans | Duree de projection |
| `elec_price_inflation` | 4 %/an | Inflation prix electricite |

---

 