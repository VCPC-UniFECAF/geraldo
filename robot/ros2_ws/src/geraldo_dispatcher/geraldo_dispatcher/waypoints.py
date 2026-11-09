import math
from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class Pose:
    x: float
    y: float
    yaw: float  # radianos

    @classmethod
    def from_dict(cls, data: dict) -> "Pose":  # FACTORY: o waypoints.yaml guarda o yaw em graus
        return cls(float(data["x"]), float(data["y"]), math.radians(data["yaw"]))

    def quaternion(self) -> tuple[float, float]:
        """(z, w) do quaternion de uma rotação em torno de Z."""
        return math.sin(self.yaw / 2), math.cos(self.yaw / 2)


def load_poses(path) -> dict[str, Pose]:
    """Lê o waypoints.yaml gerado por robot/hospital/gen_hospital.py (yaw em graus) e devolve poses em radianos."""
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))["waypoints"]
    return {wid: Pose.from_dict(w) for wid, w in data.items()}
