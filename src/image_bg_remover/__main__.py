import sys

from image_bg_remover.app import run, warm_up_inference_runtime
from image_bg_remover.inference_server import main as run_inference_server


def main() -> int:
    if "--inference-server" in sys.argv[1:]:
        return run_inference_server()
    if "--warmup-runtime" in sys.argv[1:]:
        return warm_up_inference_runtime()
    return run()


if __name__ == "__main__":
    raise SystemExit(main())
