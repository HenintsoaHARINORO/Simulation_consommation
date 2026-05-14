"""
Adaptateur de persistance : sauvegarde des résultats en CSV.
Implémente le port SimulationResultRepository.
"""
import pandas as pd
from pathlib import Path
from domain.ports.repositories import SimulationResultRepository


class CsvResultRepository(SimulationResultRepository):
    """Sauvegarde les flux horaires dans un fichier CSV."""

    def __init__(self, output_dir: str = "./results"):
        self._output_dir = Path(output_dir)
        self._output_dir.mkdir(parents=True, exist_ok=True)

    def save(self, label: str, flows: pd.DataFrame) -> None:
        safe_label = label.replace(" ", "_").replace("/", "-")
        path = self._output_dir / f"{safe_label}_flows.csv"
        flows.to_csv(path)
        print(f"  → Résultats sauvegardés : {path}")
