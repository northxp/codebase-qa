"""Command line interface for ingest."""
import argparse
import json
import sys
from pathlib import Path

from app.ingest.pipeline import run_ingest


def main():
    parser = argparse.ArgumentParser(description="Ingest a GitHub repo at a pinned commit.")
    parser.add_argument("url", help="GitHub repository URL")
    parser.add_argument("sha", help="Commit SHA (short or full)")
    parser.add_argument("--name", help="Repo name to store in DB (e.g. 'psf/requests')")
    parser.add_argument("--dest", type=Path, help="Destination directory (default: data/<name>)")
    
    args = parser.parse_args()
    
    repo_name = args.name or args.url.rstrip("/").split("/")[-2] + "/" + args.url.rstrip("/").split("/")[-1]
    dest = args.dest or Path(f"data/{repo_name.replace('/', '_')}")

    try:
        result = run_ingest(args.url, args.sha, dest, repo_name=repo_name)
        print("\n" + "="*50)
        print(f"STATUS:  {result['status'].upper()}")
        if result["status"] == "success":
            print(f"FILES:   {result['files']}")
            print(f"CHUNKS:  {result['chunks']} (inserted: {result['inserted']})")
            print("-" * 50)
            for stage, secs in result["timings"].items():
                print(f"{stage:<10}: {secs:.2f}s")
        print("="*50 + "\n")
        
        # Exit 0 on success, 0 on skipped (it's not an error), 1 on failure
        sys.exit(0)
    except Exception as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()