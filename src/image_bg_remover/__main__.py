import sys

from image_bg_remover.app import run, warm_up_inference_runtime


def main() -> int:
    if "--warmup-runtime" in sys.argv[1:]:
        return warm_up_inference_runtime()
    return run()


if __name__ == "__main__":
    raise SystemExit(main())
