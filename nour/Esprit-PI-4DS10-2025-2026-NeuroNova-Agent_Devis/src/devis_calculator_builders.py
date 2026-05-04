"""
devis_calculator_builders.py — Agrégateur des mixins de construction
─────────────────────────────────────────────────────────────────────────────
Ce fichier importe et compose les deux mixins thématiques :
  - BuildersResidential  (maison, rénovation, mixte_maison_appart)
  - BuildersCommercial   (café, hôtel, foyer, spa, sport, clinique,
                          bureau, salle fêtes, entrepôt, mixte_cafe_appart)

DevisCalculatorBuilders hérite des deux et expose tous les _build_* methods
à DevisCalculator sans duplication de code.
─────────────────────────────────────────────────────────────────────────────
"""

from .builders_residential import BuildersResidential
from .builders_commercial  import BuildersCommercial


class DevisCalculatorBuilders(BuildersResidential, BuildersCommercial):
    """
    Mixin composite — regroupe tous les builders de devis.
    Ne contient aucune logique propre : tout est dans les deux classes parentes.
    """
    pass