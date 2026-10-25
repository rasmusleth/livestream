const home = document.getElementById('home');
const away = document.getElementById('away');
const clock = document.getElementById('clock');
const notice = document.getElementById('notice');

async function refresh() {
  try {
    const response = await fetch('/api/state', {cache: 'no-store', signal: AbortSignal.timeout(1500)});
    if (!response.ok) throw Error('State unavailable');
    const state = await response.json();
    home.textContent = state.values?.home ?? '—';
    away.textContent = state.values?.away ?? '—';
    clock.textContent = state.values?.clock ?? '--:--';
    notice.hidden = state.connected && state.values !== null && state.age < 1;
    notice.textContent = state.values ? 'DATA HELD' : state.connected ? 'READING SCOREBOARD' : 'WAITING FOR REPLAY';
  } catch {
    notice.hidden = false;
    notice.textContent = clock.textContent === '--:--' ? 'WAITING FOR CONNECTION' : 'CONNECTION LOST · DATA HELD';
  } finally {
    setTimeout(refresh, 100);
  }
}
refresh();
