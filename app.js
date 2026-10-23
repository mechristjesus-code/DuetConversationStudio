const $ = (selector) => document.querySelector(selector);
const message = $('#message');
let sources = [];

function escapeHtml(value) { return String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }
function duration(ms) { if (ms == null) return '?'; const s = Math.round(ms / 1000); return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`; }
function numberOrNull(selector) { const value = $(selector).value.trim(); return value === '' ? null : Number(value); }

function updateSelectors() {
  for (const selector of ['#source-a', '#source-b']) {
    const previous = $(selector).value;
    $(selector).innerHTML = sources.map(s => `<option value="${s.id}">${escapeHtml(s.original_name)} · ${duration(s.duration_ms)}</option>`).join('');
    if (sources.some(s => String(s.id) === previous)) $(selector).value = previous;
  }
}

async function loadSources() {
  const response = await fetch('/api/sources');
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || 'Unable to load sources');
  sources = data.sources;
  updateSelectors();
  $('#sources').innerHTML = sources.length ? sources.map(s => `<article class="source"><div class="row"><strong>${escapeHtml(s.original_name)}</strong><span class="badge ${escapeHtml(s.status)}">${escapeHtml(s.status)}</span></div><div class="meta">${s.width || '?'}×${s.height || '?'} · ${duration(s.duration_ms)} · ${escapeHtml(s.video_codec || '?')} · ${s.has_audio ? 'audio' : 'silent'}</div><div class="meta">SHA-256: <code>${escapeHtml(s.sha256)}</code></div><button data-verify="${s.id}">Verify integrity</button></article>`).join('') : '<p>No sources registered yet.</p>';
  document.querySelectorAll('[data-verify]').forEach(button => button.addEventListener('click', async () => { button.disabled = true; try { await fetch(`/api/sources/${button.dataset.verify}/verify`, {method:'POST'}); await refresh(); } finally { button.disabled = false; } }));
}

async function loadGenerations() {
  const response = await fetch('/api/generations');
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || 'Unable to load generations');
  $('#generations').innerHTML = data.generations.length ? data.generations.map(g => `<article class="generation"><div class="row"><strong>Duet ${String(g.generation_number).padStart(3, '0')}</strong><span class="badge ${escapeHtml(g.render_status)}">${escapeHtml(g.render_status)}</span></div><div class="meta">${escapeHtml(g.generation_uuid)} · created ${escapeHtml(g.created_at)}</div><div>${g.render_path ? `<a href="/projects/renders/duet_${String(g.generation_number).padStart(3, '0')}.mp4">Rendered file</a>` : ''} ${g.error ? `<span class="error">${escapeHtml(g.error)}</span>` : ''}</div><button data-render="${g.id}" ${['running','queued','ok'].includes(g.render_status) ? 'disabled' : ''}>${g.render_status === 'ok' ? 'Completed' : 'Render'}</button> ${g.render_status === 'ok' ? `<button data-tiktok="${g.id}" data-generation-number="${g.generation_number}">TikTok export packet</button>` : ''}</article>`).join('') : '<p>No generations yet.</p>';
  document.querySelectorAll('[data-render]').forEach(button => button.addEventListener('click', () => renderGeneration(button.dataset.render)));
  document.querySelectorAll('[data-tiktok]').forEach(button => button.addEventListener('click', () => exportTikTok(button.dataset.tiktok, button.dataset.generationNumber)));
}

async function renderGeneration(id) {
  const response = await fetch(`/api/generations/${id}/render`, {method:'POST'});
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || 'Render could not start');
  const poll = async () => { const statusResponse = await fetch(`/api/generations/${id}/render/status`); const status = await statusResponse.json(); $('#compose-message').textContent = `Generation ${id}: ${status.render_status}`; if (['queued','running'].includes(status.render_status)) setTimeout(poll, 1000); else { await loadGenerations(); } };
  poll();
}

async function exportTikTok(id, generationNumber) {
  if (!window.confirm('Confirm you own or have permission to use every source in this duet. The app will create a local MP4 and credit packet; it will not post to TikTok.')) return;
  const username = window.prompt('Original creator username (optional, without @):', '') || '';
  const videoUrl = window.prompt('Original TikTok video URL (optional):', '') || '';
  const caption = window.prompt('Caption for the manual TikTok post (optional):', '') || '';
  const response = await fetch(`/api/generations/${id}/export/tiktok`, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({rights_confirmed:true, caption, credits:[{creator_username:username, video_url:videoUrl}]})});
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || 'TikTok export failed');
  $('#compose-message').innerHTML = `TikTok packet ready: <a href="/projects/renders/duet_${String(generationNumber).padStart(3, '0')}.tiktok.mp4">vertical MP4</a> · credit packet saved locally. Review it and post manually.`;
}

$('#import-form').addEventListener('submit', async event => { event.preventDefault(); const file = $('#video').files[0]; if (!file) return; const form = new FormData(); form.append('video', file, file.name); message.textContent = 'Copying, probing, and hashing…'; try { const response = await fetch('/api/sources', {method:'POST', body:form}); const data = await response.json(); if (!response.ok) throw new Error(data.error || 'Import failed'); message.textContent = `Registered ${data.original_name}`; event.target.reset(); await refresh(); } catch (error) { message.textContent = error.message; } });

$('#compose-form').addEventListener('submit', async event => { event.preventDefault(); const inputs = [{source_id:Number($('#source-a').value), trim_start_ms:Number($('#a-start').value || 0), trim_end_ms:numberOrNull('#a-end'), gain:Number($('#a-gain').value || 1), muted:$('#a-mute').checked}, {source_id:Number($('#source-b').value), trim_start_ms:Number($('#b-start').value || 0), trim_end_ms:numberOrNull('#b-end'), gain:Number($('#b-gain').value || 1), muted:$('#b-mute').checked}]; $('#compose-message').textContent = 'Saving recipe…'; try { const response = await fetch('/api/generations', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({inputs})}); const data = await response.json(); if (!response.ok) throw new Error(data.error || 'Could not create generation'); $('#compose-message').textContent = `Generation ${data.generation_number} saved. Starting render…`; await renderGeneration(data.id); } catch (error) { $('#compose-message').textContent = error.message; } });

async function refresh() { try { await loadSources(); await loadGenerations(); } catch (error) { message.textContent = error.message; } }
$('#refresh').addEventListener('click', refresh);
refresh();
