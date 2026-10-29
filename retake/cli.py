"""Command-line entry point:  retake audit <dataset> [options]"""
import sys
from retake import audit


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "audit":
        sys.argv = [sys.argv[0]] + sys.argv[2:]
    elif len(sys.argv) > 1 and sys.argv[1] not in ("-h", "--help"):
        print("usage: retake audit <dataset> [options]   (run 'retake audit --help' for options)")
        sys.exit(2)
    audit.main()


if __name__ == "__main__":
    main()