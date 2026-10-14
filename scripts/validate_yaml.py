"""Validate ESPHome YAML files, tolerating custom tags like !secret."""
import glob
import sys

try:
    import yaml
except ImportError:
    sys.exit("pyyaml not installed; run: pip install pyyaml")


def main() -> int:
    yaml.SafeLoader.add_multi_constructor(
        "!",
        lambda loader, suffix, node: (
            loader.construct_scalar(node)
            if isinstance(node, yaml.ScalarNode)
            else loader.construct_sequence(node)
            if isinstance(node, yaml.SequenceNode)
            else loader.construct_mapping(node)
        ),
    )
    files = sorted(
        glob.glob("**/*.yaml", recursive=True)
        + glob.glob("**/*.yml", recursive=True)
    )
    if not files:
        print("No YAML files found")
        return 1
    ok = True
    for f in files:
        try:
            with open(f) as fh:
                yaml.safe_load(fh)
            print(f"OK: {f}")
        except yaml.YAMLError as e:
            print(f"FAIL: {f}: {e}")
            ok = False
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
