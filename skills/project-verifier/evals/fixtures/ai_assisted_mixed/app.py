#!/usr/bin/env python3
import os
import sys


def main():
    mode, value = sys.argv[1:3]
    if mode == "local":
        print(value.strip())
        return
    if mode == "ai":
        if not os.environ.get("MODEL_API_KEY"):
            print("Missing required environment variable: MODEL_API_KEY")
            raise SystemExit(2)
        print("approved-ai-result")
        return
    raise SystemExit("mode must be local or ai")


if __name__ == "__main__":
    main()
