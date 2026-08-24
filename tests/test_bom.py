import pandas as pd
import pytest

from production_planning.bom import explode_bom, validate_bom_acyclic


def test_multilevel_bom_explosion():
    bom = pd.DataFrame(
        [
            {"parent_id": "FG-A", "component_id": "SUB-A", "quantity": 2.0},
            {"parent_id": "FG-A", "component_id": "COMP-A", "quantity": 1.0},
            {"parent_id": "SUB-A", "component_id": "COMP-A", "quantity": 3.0},
        ]
    )
    result = explode_bom(bom, "FG-A", 4.0)
    assert result["SUB-A"] == pytest.approx(8.0)
    assert result["COMP-A"] == pytest.approx(28.0)


def test_bom_cycle_is_rejected():
    bom = pd.DataFrame(
        [
            {"parent_id": "A", "component_id": "B", "quantity": 1.0},
            {"parent_id": "B", "component_id": "A", "quantity": 1.0},
        ]
    )
    with pytest.raises(ValueError, match="cycle"):
        validate_bom_acyclic(bom)
