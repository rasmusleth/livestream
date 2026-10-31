const $ = id => document.getElementById(id);
const video = $('video');
let dataset;
const format = seconds => `${Math.floor(seconds / 60)}:${String(Math.floor(seconds % 60)).padStart(2, '0')}`;
function update() {
  if (!dataset) return;
  const row = dataset.readings[Math.min(dataset.readings.length - 1, Math.floor(video.currentTime * dataset.fps))];
  if (!row) return;
  $('home').textContent = row.values?.home ?? '—';
  $('away').textContent = row.values?.away ?? '—';
  $('clock').textContent = row.values?.clock ?? '--:--';
  $('position').textContent = `${format(video.currentTime)} / ${format(dataset.duration)}`;
  $('age').textContent = row.age === null ? 'None yet' : `${row.age.toFixed(1)}s ago`;
  $('confidence').textContent = `${Math.round(row.confidence * 100)}%`;
  $('status').className = row.status;
  $('status').textContent = row.status === 'confirmed' ? '● Confirmed from footage' : row.status === 'held' ? `● Holding previous reading${row.age >= 1 ? ' · stale' : ''}` : '● No confirmed reading';
  $('raw').textContent = `Sample ${row.t.toFixed(1)}s · Raw: ${row.raw ? `${row.raw.home}–${row.raw.away}, ${row.raw.clock}` : 'uncertain'} · ${dataset.fps} samples per second`;
  $('evidence').textContent = Object.entries(row.segments).map(([name, values]) => `${name.padEnd(15)} ${values.map(v => v.toFixed(2)).join('  ')}`).join('\n');
}
$('regions').addEventListener('change', event => { $('boxes').hidden = !event.target.checked; });
fetch('/readings.json').then(response => { if (!response.ok) throw Error('Run reader.py to generate readings first.'); return response.json(); }).then(data => {
  dataset = data;
  for (const [name, [x, y, w, h]] of Object.entries(data.calibration.digits)) {
    const box = document.createElement('div');
    box.className = 'box'; box.title = name;
    const [width, height] = data.calibration.reference_size;
    Object.assign(box.style, {left: `${x/width*100}%`, top: `${y/height*100}%`, width: `${w/width*100}%`, height: `${h/height*100}%`});
    $('boxes').append(box);
  }
  update();
}).catch(error => { $('status').textContent = error.message; });
video.addEventListener('error', () => { $('status').textContent = 'Video could not load. Check server video path and browser codec support.'; });
for (const event of ['timeupdate', 'seeked', 'loadedmetadata']) video.addEventListener(event, update);
function tick() { update(); requestAnimationFrame(tick); }
requestAnimationFrame(tick);

$('seek-form').addEventListener('submit', event => {
  event.preventDefault();
  if (dataset) { video.pause(); video.currentTime = Math.max(0, Math.min(Number($('seek-time').value), dataset.duration - .1)); }
});

// The operator publishes positions; the server looks up confirmed values itself.
let publishing = false;
let requestInFlight = null;
$('overlay-url').value = `${location.origin}/overlay`;
async function publishPosition() {
  if (!publishing || requestInFlight || !dataset) return;
  try {
    requestInFlight = fetch('/api/playback', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({position: Math.min(video.currentTime, dataset.duration)}),
      signal: AbortSignal.timeout(1500),
    });
    const response = await requestInFlight;
    if (!response.ok) throw Error('Could not send replay');
    if (publishing) $('publish-status').textContent = video.paused ? 'Sending replay · paused at this position.' : 'Sending replay to the OBS overlay.';
  } catch {
    if (publishing) $('publish-status').textContent = 'Replay connection lost. Retrying…';
  } finally { requestInFlight = null; }
}
$('publish').addEventListener('click', async () => {
  if (!dataset) return;
  $('publish').disabled = true;
  publishing = !publishing;
  $('publish').setAttribute('aria-pressed', String(publishing));
  $('publish').textContent = publishing ? 'Stop replay output' : 'Send replay to overlay';
  try {
    if (publishing) { await publishPosition(); return; }
    // Let the last position arrive before stopping, so it cannot reactivate output.
    if (requestInFlight) await requestInFlight.catch(() => {});
    $('publish-status').textContent = 'Replay output is off. The overlay holds its last reading.';
    const response = await fetch('/api/playback', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({position: null}), signal: AbortSignal.timeout(1500)});
    if (!response.ok) throw Error('Stop failed');
  } catch { $('publish-status').textContent = 'Connection lost. The overlay will mark the output stale within two seconds.'; }
  finally { $('publish').disabled = false; }
});
setInterval(publishPosition, 100);
for (const event of ['seeked', 'pause', 'play']) video.addEventListener(event, publishPosition);
