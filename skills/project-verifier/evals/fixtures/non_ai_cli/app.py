#!/usr/bin/env python3
import csv
import sys


def main():
    source, destination = sys.argv[1:3]
    with open(source, newline="", encoding="utf-8") as input_file:
        rows = list(csv.DictReader(input_file))
    with open(destination, "w", newline="", encoding="utf-8") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=["name", "value"], lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({"name": row["name"], "value": int(row["value"]) + 1})


if __name__ == "__main__":
    main()
