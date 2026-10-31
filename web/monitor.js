const $ = id => document.getElementById(id);
$('overlay-url').value = `${location.origin}/overlay`;
async function refresh() {
  try {
    const response = await fetch('/api/state', {cache: 'no-store', signal: AbortSignal.timeout(1500)});
    if (!response.ok) throw Error('State unavailable');
    const state = await response.json();
    $('mode').textContent = state.mode === 'camera' ? 'LIVE CAMERA · EXPERIMENTAL' : 'CONTINUOUS RECORDING';
    $('source').textContent = state.source;
    sourceRunning = state.running && state.connected;
    $('home').textContent = state.values?.home ?? '—';
    $('away').textContent = state.values?.away ?? '—';
    $('clock').textContent = state.values?.clock ?? '--:--';
    $('position').textContent = state.position === null ? '—' : `${state.position.toFixed(1)}s`;
    $('delivery').textContent = state.delivery_age === null ? 'None yet' : `${state.delivery_age.toFixed(1)}s ago`;
    $('age').textContent = state.age === null ? 'None yet' : `${state.age.toFixed(1)}s ago`;
    $('status').className = state.status;
    $('status').textContent = state.status === 'confirmed' ? '● Confirmed from footage' : state.status === 'held' ? '● Holding previous reading' : '● No confirmed reading';
    $('input-status').textContent = state.error ? `Input stopped: ${state.error}` : state.connected ? '● Receiving frames' : state.running ? 'Waiting for input frames…' : 'Input ended · last values held';
    $('input-note').textContent = state.mode === 'camera' ? 'Check camera framing against the calibrated scoreboard regions before relying on these values.' : 'This recording is being recognized as it plays. No precomputed readings or publishing browser tab are needed.';
    $('diagnostics').textContent = state.diagnostics || 'No diagnostics.';
  } catch {
    $('input-status').textContent = 'Local server connection lost. Retrying…';
    $('status').className = 'held';
    $('status').textContent = '● Connection lost · last values held';
  } finally { setTimeout(refresh, 200); }
}
refresh();

let frozen = false;
let previewFrame = null;
let previewError = '';
let sourceRunning = true;
$('freeze').addEventListener('click', () => {
  frozen = !frozen;
  $('freeze').textContent = frozen ? 'Resume preview' : 'Freeze preview';
  $('freeze').setAttribute('aria-pressed', String(frozen));
  showPreviewStatus();
});
for (const [control, group] of [['show-digits', 'digit-guides'], ['show-probes', 'probe-guides']]) {
  $(control).addEventListener('change', () => { $(group).style.display = $(control).checked ? '' : 'none'; });
}
function showPreviewStatus() {
  if (!previewFrame) { $('preview-status').textContent = previewError || 'Waiting for preview…'; return; }
  const age = previewFrame.age + (performance.now() - previewFrame.received) / 1000;
  const status = frozen ? 'Frozen preview' : previewError || (!sourceRunning || age > 2 ? 'Last frame held' : 'Receiving preview');
  $('preview-status').textContent = `${status} · frame ${age.toFixed(1)}s old`;
}
async function loadGuides() {
  try {
    const response = await fetch('/api/calibration', {cache: 'no-store', signal: AbortSignal.timeout(2000)});
    if (!response.ok) throw Error('Calibration unavailable');
    const {profile, config} = await response.json();
    $('guides').setAttribute('viewBox', `0 0 ${config.reference_size.join(' ')}`);
    const shape = (group, tag, attributes, title) => {
      const element = document.createElementNS('http://www.w3.org/2000/svg', tag);
      for (const [name, value] of Object.entries(attributes)) element.setAttribute(name, value);
      const label = document.createElementNS('http://www.w3.org/2000/svg', 'title');
      label.textContent = title;
      element.append(label);
      $(group).append(element);
    };
    for (const [name, [x, y, width, height]] of Object.entries(config.digits)) {
      shape('digit-guides', 'rect', {x, y, width, height, fill: 'none', stroke: '#54ebcb', 'stroke-width': 3}, name);
    }
    for (const [name, centers] of Object.entries(config.segment_centers)) {
      for (const [x, y] of centers) shape('probe-guides', 'circle', {cx: x, cy: y, r: 5, fill: '#ffdf72', stroke: '#171d24', 'stroke-width': 2}, name);
    }
    $('profile').textContent = `Calibration: ${profile} · expected input ${config.reference_size.join(' × ')} · preview up to 2 fps`;
  } catch {
    $('profile').textContent = 'Calibration guides unavailable. Reload the monitor to retry.';
  }
}
async function refreshPreview() {
  try {
    if (frozen) return;
    const response = await fetch('/api/preview', {cache: 'no-store', signal: AbortSignal.timeout(2000)});
    if (response.status === 204) { previewError = ''; return; }
    if (!response.ok) throw Error('Preview unavailable');
    const width = Number(response.headers.get('X-Preview-Width'));
    const height = Number(response.headers.get('X-Preview-Height'));
    const age = Number(response.headers.get('X-Preview-Age'));
    const pixels = new Uint8Array(await response.arrayBuffer());
    if (!Number.isInteger(width) || !Number.isInteger(height) || width <= 0 || height <= 0 || pixels.length !== width * height * 3 || !Number.isFinite(age) || age < 0) throw Error('Invalid preview');
    if (frozen) return;
    const canvas = $('preview');
    canvas.parentElement.style.aspectRatio = `${width} / ${height}`;
    if (canvas.width !== width || canvas.height !== height) { canvas.width = width; canvas.height = height; }
    const context = canvas.getContext('2d');
    const image = context.createImageData(width, height);
    for (let src = 0, dst = 0; src < pixels.length; src += 3, dst += 4) {
      image.data[dst] = pixels[src]; image.data[dst + 1] = pixels[src + 1]; image.data[dst + 2] = pixels[src + 2]; image.data[dst + 3] = 255;
    }
    context.putImageData(image, 0, 0);
    previewFrame = {age, received: performance.now()};
    previewError = '';
    $('freeze').disabled = false;
  } catch { previewError = 'Preview connection lost'; }
  finally { showPreviewStatus(); setTimeout(refreshPreview, 500); }
}
loadGuides();
refreshPreview();
setInterval(showPreviewStatus, 500);
