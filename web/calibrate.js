/* Local profile editing. Capture and confirmed output are never changed here. */
(() => {
  const el = id => document.getElementById(id);
  const segmentNames = ['Top', 'Upper right', 'Lower right', 'Bottom', 'Lower left', 'Upper left', 'Middle'];
  const labels = {minutes_tens: 'Minutes tens', minutes_units: 'Minutes units', seconds_tens: 'Seconds tens', seconds_units: 'Seconds units', home: 'Home', away: 'Away'};
  const canonical = [[.5, .08], [.88, .25], [.88, .75], [.5, .92], [.12, .75], [.12, .25], [.5, .5]];
  let original, draft, marking = null, corners = [], hasPreview = false, busy = false, dirty = false;
  const clone = data => JSON.parse(JSON.stringify(data));
  function ready() {
    for (const id of ['align-board', 'place-digit', 'place-probe', 'test-profile', 'save-profile', 'reset-profile']) el(id).disabled = !draft || !hasPreview || busy;
    el('align-board').disabled ||= !original?.board_corners;
  }
  function hint(text) { el('edit-help').textContent = text; el('point-instruction').textContent = text; }
  function initialize(data) {
    original = clone(data.config); draft = clone(original); ready(); render();
    hint(original.board_corners ? 'Start with Align whole scoreboard: four clicks place all six digits. Fine adjustments are optional.' : 'This legacy profile has no panel outline. Restart with calibration.json for whole-scoreboard alignment, or use fine adjustments.');
  }
  const svg = (tag, attrs, title) => {
    const node = document.createElementNS('http://www.w3.org/2000/svg', tag);
    for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, value);
    const text = document.createElementNS('http://www.w3.org/2000/svg', 'title'); text.textContent = title; node.append(text); return node;
  };
  function render() {
    el('digit-guides').replaceChildren(); el('probe-guides').replaceChildren();
    if (draft.board_corners) el('digit-guides').append(svg('polygon', {points: draft.board_corners.map(point => point.join(',')).join(' '), fill: 'none', stroke: '#70bcff', 'stroke-width': 4, 'stroke-dasharray': '12 8'}, 'Central clock and scores panel'));
    for (const [name, [x, y, width, height]] of Object.entries(draft.digits)) {
      el('digit-guides').append(svg('rect', {x, y, width, height, fill: 'none', stroke: name === el('cal-digit').value ? '#ffdf72' : '#54ebcb', 'stroke-width': 3}, labels[name]));
      draft.segment_centers[name].forEach(([cx, cy], index) => {
        el('probe-guides').append(svg('circle', {cx, cy, r: 5, fill: '#ffdf72', stroke: '#171d24', 'stroke-width': 2}, `${labels[name]}: ${segmentNames[index]}`));
      });
    }
    corners.forEach(([cx, cy], index) => el('probe-guides').append(svg('circle', {cx, cy, r: 9, fill: '#ff8d69'}, `Corner ${index + 1}`)));
    if (dirty) el('profile').textContent = `Draft guides · not active in recognition · input ${draft.reference_size.join(' × ')}`;
    const point = draft.segment_centers[el('cal-digit').value][Number(el('cal-probe').value)];
    el('probe-x').value = point[0]; el('probe-y').value = point[1];
  }
  function freezeForEdit() {
    if (el('freeze').getAttribute('aria-pressed') !== 'true') el('freeze').click();
    el('show-digits').checked = el('show-probes').checked = true;
    el('digit-guides').style.display = el('probe-guides').style.display = '';
  }
  function begin(mode) {
    freezeForEdit(); marking = mode; corners = [];
    el('guides').parentElement.classList.add('editing');
    hint(mode === 'board' ? 'Central panel: top left → top right → bottom right → bottom left. Exclude numbered side panels.' : mode === 'corners' ? `Mark ${labels[el('cal-digit').value]}: top left corner, then top right, bottom right, bottom left.` : `Click the center of the ${segmentNames[Number(el('cal-probe').value)].toLowerCase()} segment, including if unlit.`);
    render();
    el('point-instruction').scrollIntoView({block: 'start'});
  }
  function changed() {
    dirty = true; marking = null; corners = [];
    el('guides').parentElement.classList.remove('editing');
    el('cal-result').textContent = 'Draft changed. Recognition still uses the active profile. Check, save, then restart to activate.';
    el('cal-diagnostics').textContent = '';
    render();
  }
  function setPoint(point) {
    const name = el('cal-digit').value;
    draft.segment_centers[name][Number(el('cal-probe').value)] = point;
    const [x, y, w, h] = draft.digits[name];
    const left = Math.min(x, point[0]), top = Math.min(y, point[1]);
    draft.digits[name] = [left, top, Math.max(x+w, point[0])-left, Math.max(y+h, point[1])-top];
    changed();
  }
  el('align-board').addEventListener('click', () => begin('board'));
  el('place-digit').addEventListener('click', () => begin('corners'));
  el('place-probe').addEventListener('click', () => begin('probe'));
  for (const id of ['cal-digit', 'cal-probe']) el(id).addEventListener('change', () => {
    marking = null; corners = []; el('guides').parentElement.classList.remove('editing');
    if (draft) render();
  });
  el('guides').parentElement.addEventListener('pointerdown', async event => {
    if (busy || !marking || !draft || event.button !== 0) return;
    event.preventDefault();
    const rect = el('preview').getBoundingClientRect();
    const [width, height] = draft.reference_size;
    const point = [Math.round((event.clientX-rect.left)/rect.width*width), Math.round((event.clientY-rect.top)/rect.height*height)];
    const margin = marking === 'board' ? 0 : 6;
    if (point[0] < margin || point[1] < margin || point[0] >= width-margin || point[1] >= height-margin) {
      hint('Choose a point inside the image, leaving room for the probe sample.'); return;
    }
    if (marking === 'probe') { setPoint(point); hint('Probe moved. Check it against the segment center.'); return; }
    corners.push(point);
    if (corners.length < 4) { render(); hint(`Next: ${['top left', 'top right', 'bottom right', 'bottom left'][corners.length]} corner.`); return; }
    // Ordered convex corners allow rotation and skew; individual probes remain adjustable.
    const cross = corners.map((p, i) => {
      const q = corners[(i+1)%4], r = corners[(i+2)%4];
      return (q[0]-p[0])*(r[1]-q[1])-(q[1]-p[1])*(r[0]-q[0]);
    });
    if (!cross.every(value => value > 0)) {
      corners = []; render(); hint('Corners must form a convex digit outline in the requested order. Start with top left again.'); return;
    }
    if (marking === 'board') {
      const selected = clone(corners);
      busy = true; ready();
      try {
        const response = await fetch('/api/calibration/align', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({corners: selected}), signal: AbortSignal.timeout(5000)});
        const result = await response.json();
        if (!response.ok) throw Error(result.error || 'Alignment failed');
        draft = result.config;
        changed();
        hint('All six digits and 42 probes aligned. Check against the latest frame; fine-tune only where needed, then save and restart.');
      } catch (error) {
        corners = []; render(); hint(`Alignment failed: ${error.message}. Mark the panel again.`);
      } finally { busy = false; ready(); }
      return;
    }
    const [a, b, c, d] = corners;
    const name = el('cal-digit').value;
    draft.segment_centers[name] = canonical.map(([u, v]) => [
      Math.round((1-u)*(1-v)*a[0]+u*(1-v)*b[0]+u*v*c[0]+(1-u)*v*d[0]),
      Math.round((1-u)*(1-v)*a[1]+u*(1-v)*b[1]+u*v*c[1]+(1-u)*v*d[1])]);
    const xs = corners.map(p => p[0]), ys = corners.map(p => p[1]);
    draft.digits[name] = [Math.min(...xs), Math.min(...ys), Math.max(...xs)-Math.min(...xs), Math.max(...ys)-Math.min(...ys)];
    changed(); hint('Seven probes placed. Adjust any probe that misses its stroke, then select the next digit.');
  });
  el('set-probe').addEventListener('click', () => {
    if (!draft || busy) return;
    const x = Number(el('probe-x').value), y = Number(el('probe-y').value);
    const [width, height] = draft.reference_size;
    if (!Number.isInteger(x) || !Number.isInteger(y) || x < 6 || x >= width-6 || y < 6 || y >= height-6) {
      hint('Enter integer source coordinates at least six pixels inside the image.'); return;
    }
    setPoint([x, y]);
  });
  el('reset-profile').addEventListener('click', () => {
    draft = clone(original); dirty = false; marking = null; corners = [];
    el('guides').parentElement.classList.remove('editing'); render();
    el('profile').textContent = 'Active profile guides restored';
    hint('Active guides restored. Select a digit to begin again.');
    el('cal-result').textContent = 'Edits discarded. Recognition was unchanged.';
    el('cal-diagnostics').textContent = '';
  });
  el('preview-zoom').addEventListener('input', () => {
    el('guides').parentElement.style.width = `${Number(el('preview-zoom').value)*100}%`;
  });
  async function submit(action) {
    marking = null; corners = []; el('guides').parentElement.classList.remove('editing');
    busy = true; ready();
    try {
      const response = await fetch(`/api/calibration/${action}`, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(draft), signal: AbortSignal.timeout(5000)});
      const result = await response.json();
      if (!response.ok) throw Error(result.error || 'Calibration request failed');
      if (action === 'save') {
        el('cal-result').textContent = 'Saved locally; this profile is NOT active yet. Stop this server (Ctrl+C), then restart your server command with --calibration data/calibration.local.json.';
        el('cal-diagnostics').textContent = result.message;
      } else {
        el('cal-result').textContent = `Latest preview check · frame ${result.preview_age.toFixed(1)}s old · ${result.raw ? `Raw reading ${result.raw.clock}, ${result.raw.home}–${result.raw.away}` : 'Incomplete reading'} · not confirmed`;
        el('cal-diagnostics').textContent = Object.entries(result.digits).map(([name, value]) => `${labels[name]}: ${value ?? 'unknown'} | segment levels ${result.segments[name].join(', ')}`).join('\n');
      }
    } catch (error) { el('cal-result').textContent = error.message; }
    finally { busy = false; ready(); }
  }
  el('test-profile').addEventListener('click', () => submit('test'));
  el('save-profile').addEventListener('click', () => submit('save'));
  window.addEventListener('calibration-loaded', event => initialize(event.detail));
  if (window.calibrationData) initialize(window.calibrationData);
  window.addEventListener('preview-ready', () => { hasPreview = true; ready(); });
  if (!el('freeze').disabled) { hasPreview = true; ready(); }
})();
