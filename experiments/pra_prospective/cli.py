"""Command line interface for the frozen prospective evaluation workflow."""
import argparse
import json
from pathlib import Path

from .core import attach_reviews, export_anonymous, import_ratings, report, seal, verify


def main(argv=None):
    parser = argparse.ArgumentParser(description="Freeze and score a prospective PRA comparison without running models")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("seal")
    p.add_argument("protocol", type=Path)
    p.add_argument("study", type=Path)
    p = sub.add_parser("attach-reviews")
    p.add_argument("study", type=Path)
    p = sub.add_parser("verify")
    p.add_argument("study", type=Path)
    p = sub.add_parser("export")
    p.add_argument("study", type=Path)
    p.add_argument("output", type=Path)
    p.add_argument("--seed", type=int, required=True)
    p = sub.add_parser("import-ratings")
    p.add_argument("study", type=Path)
    p.add_argument("packet", type=Path)
    p.add_argument("ratings", type=Path)
    p = sub.add_parser("report")
    p.add_argument("study", type=Path)
    p.add_argument("output", type=Path)
    args = parser.parse_args(argv)
    if args.command == "seal":
        value = seal(args.protocol, args.study)
    elif args.command == "attach-reviews":
        value = attach_reviews(args.study)
    elif args.command == "verify":
        value = verify(args.study)
    elif args.command == "export":
        value = export_anonymous(args.study, args.output, args.seed)
    elif args.command == "import-ratings":
        value = import_ratings(args.study, args.packet, args.ratings)
    else:
        value = report(args.study, args.output)
    print(json.dumps(value, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
