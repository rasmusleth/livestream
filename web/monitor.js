const $ = id => document.getElementById(id);
$('overlay-url').value = `${location.origin}/overlay`;
async function refresh() {
  try {
    const response = await fetch('/api/state', {cache: 'no-store', signal: AbortSignal.timeout(1500)});
    if (!response.ok) throw Error('State unavailable');
    const state = await response.json();
    $('mode').textContent = state.mode === 'camera' ? 'LIVE CAMERA · EXPERIMENTAL' : 'CONTINUOUS RECORDING';
    $('source').textContent = state.source;
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
