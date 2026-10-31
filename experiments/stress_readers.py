"""Compare candidates on labelled held-out frames with deliberate calibration error."""
import argparse
import json
from pathlib import Path

from compare_readers import RegionReader, frames, confirmed_rows

OFFSETS = ((0,0),(-5,0),(5,0),(0,-5),(0,5),(-10,0),(10,0),(0,-10),(0,10))


def main():
    import cv2
    import numpy as np
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('video', type=Path)
    parser.add_argument('--calibration', required=True, type=Path)
    parser.add_argument('--template', type=Path, default=Path('calibration.json'))
    parser.add_argument('--labels', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--skip-ocr', action='store_true')
    parser.add_argument('--sequence-radius', type=int, default=5,
                        help='Samples before/after each reviewed anchor (default: 5)')
    args = parser.parse_args()
    if args.sequence_radius < 0:
        parser.error('--sequence-radius must be nonnegative')
    config = json.loads(args.calibration.read_text())
    labels = {round(label['t']*config['sample_fps']): label for label in json.loads(args.labels.read_text()) if label.get('split') == 'heldout'}
    if not labels:
        parser.error('At least one heldout label is required')
    reader = RegionReader(config, json.loads(args.template.read_text()))
    sequences = {(anchor, offset, method): [] for anchor in labels for offset in OFFSETS
                 for method in (('regions',) if args.skip_ocr else ('regions','ocr'))}
    width, height = config['reference_size']
    radius = args.sequence_radius
    for index, payload in enumerate(frames(args.video, (width, height), config['sample_fps'], max(labels)+radius+1)):
        anchors = [anchor for anchor in labels if abs(index-anchor) <= radius]
        if not anchors:
            continue
        frame = np.frombuffer(payload, np.uint8).reshape(height, width, 3)
        for dx, dy in OFFSETS:
            shifted = cv2.warpAffine(frame, np.float32([[1,0,dx],[0,1,dy]]), (width,height))
            masks = reader.masks(shifted)
            methods = [('regions',reader.read)] + ([] if args.skip_ocr else [('ocr',reader.ocr)])
            for name, method in methods:
                value, digits = method(masks)
                for anchor in anchors:
                    # Only the anchor is labelled. Do not extend its truth to a
                    # surrounding sequence that may include clock/score changes.
                    expected = labels[anchor]['values'] if index == anchor else None
                    sequences[anchor,(dx,dy),name].append({
                        't':round(index/config['sample_fps'],3), 'anchor_t':labels[anchor]['t'],
                        'offset':[dx,dy], 'method':name, 'raw':value, 'digits':digits,
                        'evidence':reader.inspect(masks) if name == 'regions' else None,
                        'expected':expected,
                        'correct':None if value is None or expected is None else value == expected})
    results = []
    for sequence in sequences.values():
        confirmed = confirmed_rows([row['raw'] for row in sequence], config['sample_fps'])
        for row, state in zip(sequence, confirmed):
            row.update({key:state[key] for key in ('values','status','age')})
            results.append(row)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(results, indent=2)+'\n')


if __name__ == '__main__':
    main()
