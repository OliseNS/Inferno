"""
Optional sanity check for the exported NCNN fire/smoke model (not used at runtime).
Run from project root: python scripts/ncnn_smoke_test.py
"""
import sys
from pathlib import Path

import numpy as np
import ncnn
import torch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = PROJECT_ROOT / "models" / "fire_smoke_yolo11_ncnn_model"


def test_inference():
    torch.manual_seed(0)
    in0 = torch.rand(1, 3, 224, 224, dtype=torch.float)
    out = []

    param = MODEL_DIR / "model.ncnn.param"
    bin_path = MODEL_DIR / "model.ncnn.bin"
    if not param.is_file() or not bin_path.is_file():
        print(f"Missing NCNN files under {MODEL_DIR}", file=sys.stderr)
        sys.exit(1)

    with ncnn.Net() as net:
        net.load_param(str(param))
        net.load_model(str(bin_path))

        with net.create_extractor() as ex:
            ex.input("in0", ncnn.Mat(in0.squeeze(0).numpy()).clone())

            _, out0 = ex.extract("out0")
            out.append(torch.from_numpy(np.array(out0)).unsqueeze(0))

    if len(out) == 1:
        return out[0]
    return tuple(out)


if __name__ == "__main__":
    print(test_inference())
