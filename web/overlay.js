const home = document.getElementById('home');
const away = document.getElementById('away');
const clock = document.getElementById('clock');
const notice = document.getElementById('notice');
const sourceLabel = document.getElementById('source-label');

async function refresh() {
  try {
    const response = await fetch('/api/state', {cache: 'no-store', signal: AbortSignal.timeout(1500)});
    if (!response.ok) throw Error('State unavailable');
    const state = await response.json();
    sourceLabel.textContent = state.mode === 'camera' ? 'LIVE' : 'REPLAY';
    home.textContent = state.values?.home ?? '—';
    away.textContent = state.values?.away ?? '—';
    clock.textContent = state.values?.clock ?? '--:--';
    notice.hidden = state.connected && state.values !== null && state.age < 1;
    notice.textContent = state.values ? 'DATA HELD' : state.connected ? 'READING SCOREBOARD' : state.mode === 'camera' ? 'WAITING FOR CAMERA' : 'WAITING FOR REPLAY';
  } catch {
    notice.hidden = false;
    notice.textContent = clock.textContent === '--:--' ? 'WAITING FOR CONNECTION' : 'CONNECTION LOST · DATA HELD';
  } finally {
    setTimeout(refresh, 100);
  }
}
refresh();
