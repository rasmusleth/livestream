"""Summarize saved local comparison reports; no optional image dependencies required."""
import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('reports', nargs='+', type=Path)
    args = parser.parse_args()
    print('| Recording | Method | Raw coverage | Fresh confirmation | Reviewed raw correct / wrong / unknown | Reviewed fresh wrong |')
    print('| --- | --- | --- | --- | --- | --- |')
    for path in args.reports:
        report = json.loads(path.read_text())
        for name, metrics in report['metrics'].items():
            count = metrics['samples']
            reviewed = ' / '.join(str(metrics[k]) for k in ('reviewed_raw_correct','reviewed_raw_wrong','reviewed_raw_unknown'))
            print(f"| {report['video']} | {name} | {metrics['raw_available']}/{count} ({100*metrics['raw_available']/count:.1f}%) | {metrics['fresh_confirmed']}/{count} ({100*metrics['fresh_confirmed']/count:.1f}%) | {reviewed} | {metrics['reviewed_fresh_wrong']} |")


if __name__ == '__main__':
    main()
