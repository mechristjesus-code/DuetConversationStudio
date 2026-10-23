function showStatus(message, isError = false) {
    const banner = document.getElementById('status-banner');
    if (!banner) return;
    banner.textContent = message;
    banner.style.display = 'block';
    banner.style.borderLeftColor = isError ? '#ef4444' : '#6200ee';
    banner.style.background = isError ? '#2a1215' : '#2c2c2c';
    banner.style.color = isError ? '#fca5a5' : '#e0e0e0';
}

function switchTab(tabName) {
    document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
    
    document.getElementById('tab-' + tabName).classList.add('active');
    event.target.classList.add('active');

    if (tabName === 'studio') {
        loadAssets();
    } else if (tabName === 'map') {
        loadGenerations();
    } else if (tabName === 'lab') {
        loadTurns();
    }
}

async function loadAssets() {
    try {
        const res = await fetch('/api/assets');
        const assets = await res.json();
        
        const listDiv = document.getElementById('assets-list');
        const select1 = document.getElementById('asset1-select');
        const select2 = document.getElementById('asset2-select');
        
        select1.innerHTML = '';
        select2.innerHTML = '';
        
        if (assets.length === 0) {
            listDiv.innerHTML = '<p>No assets uploaded yet.</p>';
            return;
        }
        
        let html = '<table><tr><th>ID</th><th>File</th><th>Duration</th><th>Resolution</th></tr>';
        assets.forEach(a => {
            html += `<tr><td>${a.asset_id}</td><td>${a.file_path.split('/').pop()}</td><td>${a.duration.toFixed(2)}s</td><td>${a.width}x${a.height}</td></tr>`;
            
            const opt = document.createElement('option');
            opt.value = a.asset_id;
            opt.textContent = `${a.asset_id} (${a.file_path.split('/').pop()} - ${a.duration.toFixed(1)}s)`;
            select1.appendChild(opt.cloneNode(true));
            select2.appendChild(opt);
        });
        html += '</table>';
        listDiv.innerHTML = html;
    } catch (err) {
        console.error('Failed to load assets', err);
        showStatus('Failed to load assets', true);
    }
}

async function uploadVideo(e) {
    e.preventDefault();
    const fileInput = document.getElementById('video-file');
    if (!fileInput.files[0]) return;

    const formData = new FormData();
    formData.append('video', fileInput.files[0]);

    showStatus('Uploading and inspecting video metadata...');
    try {
        const res = await fetch('/api/assets/upload', {
            method: 'POST',
            body: formData
        });
        const data = await res.json();
        if (data.success) {
            showStatus('Asset uploaded successfully: ' + data.asset_id);
            fileInput.value = '';
            loadAssets();
        } else {
            showStatus('Upload failed: ' + data.error, true);
        }
    } catch (err) {
        console.error('Upload error', err);
        showStatus('Upload error occurred', true);
    }
}

async function renderDuet() {
    const asset1_id = document.getElementById('asset1-select').value;
    const asset2_id = document.getElementById('asset2-select').value;
    const layout = document.getElementById('layout-select').value;

    if (!asset1_id || !asset2_id) {
        showStatus('Please select both Video A and Video B', true);
        return;
    }

    showStatus('Rendering Duet via FFmpeg... Please wait.');
    try {
        const res = await fetch('/api/render/duet', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ asset1_id, asset2_id, layout })
        });
        const data = await res.json();
        if (data.success) {
            showStatus('Duet rendered successfully! Generation ID: ' + data.generation_id);
            const previewCard = document.getElementById('preview-card');
            const outputVideo = document.getElementById('output-video');
            const outputInfo = document.getElementById('output-info');
            const downloadBtn = document.getElementById('download-btn');

            outputVideo.src = data.output_url;
            downloadBtn.href = data.output_url;
            outputInfo.textContent = `Generation ID: ${data.generation_id} | Output Asset ID: ${data.output_asset_id}`;
            previewCard.style.display = 'block';
            loadAssets();
        } else {
            showStatus('Render failed: ' + data.error, true);
        }
    } catch (err) {
        console.error('Render error', err);
        showStatus('Render error occurred', true);
    }
}

async function loadGenerations() {
    try {
        const res = await fetch('/api/generations');
        const gens = await res.json();
        const listDiv = document.getElementById('generations-list');
        
        if (gens.length === 0) {
            listDiv.innerHTML = '<p>No generations recorded yet.</p>';
            return;
        }
        
        let html = '<table><tr><th>Generation ID</th><th>Layout</th><th>Parents</th><th>Output Asset</th><th>Timestamp</th></tr>';
        gens.forEach(g => {
            html += `<tr><td>${g.generation_id}</td><td>${g.layout}</td><td>${g.parent_assets}</td><td>${g.output_asset_id}</td><td>${g.created_at}</td></tr>`;
        });
        html += '</table>';
        listDiv.innerHTML = html;
    } catch (err) {
        console.error('Failed to load generations', err);
    }
}

async function loadTurns() {
    try {
        const res = await fetch('/api/turns');
        const turns = await res.json();
        const listDiv = document.getElementById('turns-list');
        
        if (turns.length === 0) {
            listDiv.innerHTML = '<p>No conversation turns recorded yet.</p>';
            return;
        }
        
        let html = '<table><tr><th>Turn ID</th><th>Segment</th><th>Transcript</th><th>Replies To</th><th>Relationship</th></tr>';
        turns.forEach(t => {
            html += `<tr><td>${t.turn_id}</td><td>${t.segment_id || '-'}</td><td>${t.transcript}</td><td>${t.reply_to || '-'}</td><td>${t.relationship}</td></tr>`;
        });
        html += '</table>';
        listDiv.innerHTML = html;
    } catch (err) {
        console.error('Failed to load turns', err);
    }
}

async function saveTurn() {
    const segment_id = document.getElementById('turn-segment').value;
    const transcript = document.getElementById('turn-transcript').value;
    const reply_to = document.getElementById('turn-reply').value;
    const relationship = document.getElementById('turn-relation').value;

    if (!transcript) {
        showStatus('Please enter a transcript', true);
        return;
    }

    try {
        const res = await fetch('/api/turns', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ segment_id, transcript, reply_to, relationship })
        });
        const data = await res.json();
        if (data.success) {
            showStatus('Conversation turn saved successfully!');
            document.getElementById('turn-segment').value = '';
            document.getElementById('turn-transcript').value = '';
            document.getElementById('turn-reply').value = '';
            loadTurns();
        } else {
            showStatus('Failed to save turn', true);
        }
    } catch (err) {
        console.error('Save turn error', err);
        showStatus('Save turn error occurred', true);
    }
}

// Initial load
loadAssets();
