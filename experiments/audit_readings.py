"""Audit saved independent candidate timelines against explicit per-field reviews.

No recognition, capture, optional packages, or runtime output changes. Unknown
physical truth is measured separately, never counted as correct or wrong.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re

FIELDS = ('home', 'away', 'clock')
STATUSES = ('confirmed', 'held', 'unknown')


def number(value):
    return type(value) in (int, float) and math.isfinite(value)


def valid_value(value, field):
    if field != 'clock':
        return type(value) is int and 0 <= value <= 9
    return isinstance(value,str) and re.fullmatch(r'(?:[0-9]{2}:[0-5][0-9]|00:[0-5][0-9]\.[0-9])',value) is not None


def timeline(report):
    fps = report.get('fps')
    rows = report.get('independent_rows')
    if not number(fps) or fps <= 0 or not isinstance(rows,list) or not rows:
        raise ValueError('Expected positive fps and a nonempty independent timeline')
    at = {field:None for field in FIELDS}
    previous = {field:None for field in FIELDS}
    for index,row in enumerate(rows):
        if not isinstance(row,dict) or not isinstance(row.get('fields'),dict):
            raise ValueError('Each timeline row needs named field states')
        t = row.get('t')
        if not number(t) or abs(t-index/fps) > 1e-6:
            raise ValueError('Timeline must use its complete source sample grid from zero')
        for field in FIELDS:
            state = row['fields'].get(field)
            if not isinstance(state,dict) or not {'value','observed','status','age'} <= state.keys():
                raise ValueError('Each timeline field needs value, observed, status and age')
            value,observed,status,age = (state[key] for key in ('value','observed','status','age'))
            if status not in STATUSES:
                raise ValueError('Invalid field status')
            if any(v is not None and not valid_value(v,field) for v in (value,observed)):
                raise ValueError('Invalid observed or confirmed field value')
            if status == 'confirmed':
                if value is None or value != observed or not number(age) or abs(age) > 1e-9:
                    raise ValueError('Fresh output must equal an observation and have zero age')
                at[field] = t
            elif value != previous[field]:
                raise ValueError('A held/unknown field must not change its confirmed value')
            if (status == 'unknown' and value is not None) or (status == 'held' and value is None):
                raise ValueError('Field value contradicts its status')
            if value is None:
                if age is not None:
                    raise ValueError('Unknown output cannot have confirmation age')
            elif at[field] is None or not number(age) or age < 0 or abs(age-round(t-at[field],3)) > .001:
                raise ValueError('Confirmation age must follow source time without refresh on holds')
            previous[field] = value
    return fps,rows


def audit(report, review):
    """Return explicit readable correctness, unreadable exposure and coverage counts."""
    if not isinstance(report,dict) or not isinstance(review,dict):
        raise ValueError('Report and review must be JSON objects')
    digest = report.get('video_sha256')
    if not isinstance(digest,str) or re.fullmatch('[0-9a-f]{64}',digest) is None:
        raise ValueError('Report needs an input video SHA-256')
    if review.get('video_sha256') != digest:
        raise ValueError('Review and report refer to different video content')
    fps,rows = timeline(report)
    if not number(review.get('fps')) or review['fps'] != fps:
        raise ValueError('Review sample rate differs from report')
    if not isinstance(review.get('method'),str) or not review['method'].strip():
        raise ValueError('Describe how the source frames were reviewed')
    entries = review.get('reviews')
    if not isinstance(entries,list) or not entries:
        raise ValueError('Expected explicit source-frame reviews')
    counts = {field:dict.fromkeys(('readable','unreadable','observed_correct','observed_wrong','observed_unknown',
                                  'fresh_correct','fresh_wrong','readable_held','readable_unknown',
                                  'held_value_correct','held_value_wrong','unreadable_observed',
                                  'unreadable_fresh','unreadable_held','unreadable_unknown'),0) for field in FIELDS}
    checks = []
    indices = set()
    for entry in entries:
        if not isinstance(entry,dict):
            raise ValueError('Each review must be a named source sample')
        t = entry.get('t')
        if not number(t) or t < 0 or abs(t*fps-round(t*fps)) > 1e-6:
            raise ValueError('Review times must be nonnegative exact source-grid timestamps')
        index = round(t*fps)
        if index >= len(rows) or index in indices:
            raise ValueError('Review index is duplicated or outside the timeline')
        indices.add(index)
        fields = entry.get('fields')
        if not isinstance(fields,dict) or not fields or set(fields)-set(FIELDS):
            raise ValueError('Review only named clock/home/away fields; omitted fields remain unreviewed')
        checked = {}
        for field,label in fields.items():
            if not isinstance(label,dict) or set(label) not in ({'value'},{'unreadable'}):
                raise ValueError('Each field needs exactly value or an unreadable reason')
            state = rows[index]['fields'][field]
            count = counts[field]
            readable = 'value' in label
            if readable:
                expected = label['value']
                if not valid_value(expected,field):
                    raise ValueError('A readable field needs a valid value; use unreadable for unknown truth')
                count['readable'] += 1
                observed = state['observed']
                count['observed_unknown' if observed is None else 'observed_correct' if observed == expected else 'observed_wrong'] += 1
                if state['status'] == 'confirmed':
                    count['fresh_correct' if state['value'] == expected else 'fresh_wrong'] += 1
                else:
                    count['readable_'+state['status']] += 1
                    if state['status'] == 'held':
                        count['held_value_correct' if state['value'] == expected else 'held_value_wrong'] += 1
            else:
                if not isinstance(label['unreadable'],str) or not label['unreadable'].strip():
                    raise ValueError('Explain why physical truth is unreadable')
                count['unreadable'] += 1
                count['unreadable_observed'] += state['observed'] is not None
                count['unreadable_fresh' if state['status'] == 'confirmed' else 'unreadable_'+state['status']] += 1
            checked[field] = {'review':dict(label), 'state':dict(state)}
        checks.append({'t':t, 'fields':checked})
    for field,count in counts.items():
        count['unreviewed'] = len(rows)-count['readable']-count['unreadable']
        count['all_observed_available'] = sum(row['fields'][field]['observed'] is not None for row in rows)
        count['all_fresh_confirmed'] = sum(row['fields'][field]['status'] == 'confirmed' for row in rows)
    return {'video_sha256':digest,'fps':fps,'samples':len(rows),'method':review['method'],
            'counts':counts,'checks':sorted(checks,key=lambda check:check['t']),
            'interpretation':'Unreadable means no physical truth was assigned. Fresh output on such a frame is a review risk, not a proven error or success. Coverage is not accuracy.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report',type=Path)
    parser.add_argument('review',type=Path)
    parser.add_argument('--output',required=True,type=Path)
    args = parser.parse_args()
    if args.output.resolve() in (args.report.resolve(),args.review.resolve()):
        parser.error('Output must not overwrite report or review inputs')
    try:
        report_bytes,review_bytes = args.report.read_bytes(),args.review.read_bytes()
        result = audit(json.loads(report_bytes),json.loads(review_bytes))
        result['report_sha256'] = hashlib.sha256(report_bytes).hexdigest()
        result['review_sha256'] = hashlib.sha256(review_bytes).hexdigest()
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(result,indent=2)+'\n')
    except (OSError,ValueError,KeyError,TypeError) as error:
        parser.error(str(error))
    print('| Field | Readable | Fresh correct / wrong | Held / unknown | Unreadable | Fresh on unreadable |')
    print('| --- | --- | --- | --- | --- | --- |')
    for field,c in result['counts'].items():
        print(f"| {field} | {c['readable']} | {c['fresh_correct']} / {c['fresh_wrong']} | {c['readable_held']} / {c['readable_unknown']} | {c['unreadable']} | {c['unreadable_fresh']} |")
    print(result['interpretation'])


if __name__ == '__main__':
    main()
