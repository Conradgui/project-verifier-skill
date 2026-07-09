#!/usr/bin/env python3
import json
import sys


def main():
    prompt = sys.argv[1]
    print(json.dumps({"answer": f"local:{prompt}", "model": "fixture-v1"}))


if __name__ == "__main__":
    main()
