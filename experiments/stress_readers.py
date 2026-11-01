"""Compare candidates on labelled held-out frames with deliberate calibration error."""
import argparse
import json
from pathlib import Path

from compare_readers import RegionReader, frames


def main():
    import cv2
    import numpy as np
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('video', type=Path)
    parser.add_argument('--calibration', required=True, type=Path)
    parser.add_argument('--template', type=Path, default=Path('calibration.json'))
    parser.add_argument('--labels', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    config = json.loads(args.calibration.read_text())
    labels = {round(label['t']*config['sample_fps']): label for label in json.loads(args.labels.read_text()) if label.get('split') == 'heldout'}
    if not labels:
        parser.error('At least one heldout label is required')
    reader = RegionReader(config, json.loads(args.template.read_text()))
    results = []
    width, height = config['reference_size']
    for index, payload in enumerate(frames(args.video, (width, height), config['sample_fps'], max(labels)+1)):
        if index not in labels:
            continue
        frame = np.frombuffer(payload, np.uint8).reshape(height, width, 3)
        for dx, dy in ((0,0),(-5,0),(5,0),(0,-5),(0,5),(-10,0),(10,0),(0,-10),(0,10)):
            shifted = cv2.warpAffine(frame, np.float32([[1,0,dx],[0,1,dy]]), (width,height))
            masks = reader.masks(shifted)
            for name, method in (('regions',reader.read),('ocr',reader.ocr)):
                value, digits = method(masks)
                results.append({'t':labels[index]['t'], 'offset':[dx,dy], 'method':name,
                    'raw':value, 'digits':digits, 'expected':labels[index]['values'],
                    'correct':None if value is None else value == labels[index]['values']})
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(results, indent=2)+'\n')


if __name__ == '__main__':
    main()
