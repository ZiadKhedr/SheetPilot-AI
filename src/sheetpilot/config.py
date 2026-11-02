from dataclasses import dataclass
from pathlib import Path
import os

from dotenv import load_dotenv

ROOT = Path(os.getenv("SHEETPILOT_ROOT", str(Path(__file__).resolve().parents[2]))).resolve()


@dataclass
class Settings:
    data_dir: Path
    access_token: str = ""
    read_token: str = ""

    @classmethod
    def from_env(cls):
        load_dotenv(ROOT / ".env", override=False)
        path = Path(os.getenv("SHEETPILOT_DATA_DIR", str(ROOT / ".data")))
        if not path.is_absolute():
            path = ROOT / path
        return cls(path, os.getenv("SHEETPILOT_ACCESS_TOKEN", ""), os.getenv("SHEETPILOT_READ_TOKEN", ""))
