from __future__ import annotations

import json
from pathlib import Path
from typing import Union

from graphlens_agent.schema import GraphDocument
from graphlens_agent.validator import validate_graph_document


def load_graph_json(path: Union[str, Path]) -> GraphDocument:
    with Path(path).open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return validate_graph_document(payload)
