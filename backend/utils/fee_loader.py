import yaml
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
FEE_FILE = BASE_DIR / "config" / "fee_structure.yaml"


def load_fee_structure():
    with open(FEE_FILE, "r") as file:
        data = yaml.safe_load(file)
    return data


def get_class_fee(class_code):

    data = load_fee_structure()

    for category in data.values():
        for cls in category["classes"]:
            if cls["code"] == class_code:
                return cls

    return None