// ==========================================
// 1. Dark Mode / Theme Logic
// ==========================================
function initTheme() {
    const savedTheme = localStorage.getItem('theme') || 'dark';
    document.documentElement.setAttribute('data-theme', savedTheme);
    updateThemeButton(savedTheme);
}

function toggleTheme() {
    const currentTheme = document.documentElement.getAttribute('data-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
    updateThemeButton(newTheme);
    loadHistory();
}

function updateThemeButton(theme) {
    const btn = document.getElementById('themeToggle');
    if (btn) btn.innerText = theme === 'dark' ? '☀️' : '🌙';
}

initTheme();

// ==========================================
// 2. Custom Chart.js Plugin for Center Text
// ==========================================
const centerTextPlugin = {
    id: 'centerText',
    afterDraw(chart, args, options) {
        if (!chart.config.options.plugins.centerText) return;
        const { ctx, chartArea: { top, bottom, left, right, width, height } } = chart;
        ctx.save();
        const centerX = left + width / 2;
        const centerY = top + height / 2;

        ctx.font = 'bold 38px "Segoe UI"';
        ctx.fillStyle = chart.config.options.plugins.centerText.color;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(chart.config.options.plugins.centerText.value, centerX, centerY - 5);

        ctx.font = '14px "Segoe UI"';
        ctx.fillStyle = getComputedStyle(document.documentElement).getPropertyValue('--text-muted').trim();
        ctx.fillText(chart.config.options.plugins.centerText.label, centerX, centerY + 30);
        ctx.restore();
    }
};
Chart.register(centerTextPlugin);

// ==========================================
// 3. Initialize Gauges
// ==========================================
const vitalCharts = {};

function createGauge(key, canvasId, percentageValue, displayValue, unit, color) {
    const ctx = document.getElementById(canvasId).getContext('2d');
    if (vitalCharts[key]) vitalCharts[key].destroy();

    vitalCharts[key] = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: [unit],
            datasets: [{
                data: [percentageValue, 100 - percentageValue],
                backgroundColor: [color, getComputedStyle(document.documentElement).getPropertyValue('--card-border').trim()],
                borderWidth: 0,
                cutout: '78%',
                circumference: 270,
                rotation: 225
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: { duration: 500 },
            plugins: {
                legend: { display: false },
                tooltip: { enabled: false },
                centerText: { value: displayValue, label: unit, color: color }
            }
        }
    });
}

function renderVital(key, canvasId, value, maxValue, unit, statusText, statusClass) {
    const hasValue = value !== null && value !== undefined && value !== '' && Number.isFinite(Number(value));
    const numericValue = hasValue ? Number(value) : 0;
    const progress = Math.max(0, Math.min((numericValue / maxValue) * 100, 100));
    const status = document.getElementById(`${key}Status`);
    status.textContent = hasValue ? statusText : 'NO DATA';
    status.className = `vital-status${hasValue && statusClass ? ` ${statusClass}` : ''}`;

    const primaryColor = getComputedStyle(document.documentElement).getPropertyValue('--primary').trim();
    const displayValue = hasValue
        ? (key === 'temp' || key === 'sleep' || key === 'radiation' ? numericValue.toFixed(1) : Math.round(numericValue))
        : '--';
    createGauge(key, canvasId, progress, displayValue, unit, primaryColor);
}

// ==========================================
// 4. Load History & Update Gauges
// ==========================================
async function loadHistory() {
  try {
    const res = await fetch('/api/health/history');
    if (res.status === 401) { window.location.href = '/login'; return; }
    
    const rows = await res.json();
    
    const tbody = document.querySelector('#historyTable tbody');
    tbody.innerHTML = '';
    rows.forEach(r => {
      const tr = document.createElement('tr');
      const cls = r.risk_status.toLowerCase().replace(' ', '-');
      tr.innerHTML = `
        <td>${r.recorded_at}</td>
        <td>${r.heart_rate}</td>
        <td>${r.systolic_bp}/${r.diastolic_bp}</td>
        <td>${r.spo2}%</td>
        <td>${r.body_temp}</td>
        <td>${r.sleep_hours}</td>
        <td>${r.activity_minutes}</td>
        <td><span class="badge ${cls}">${r.risk_status}</span></td>
      `;
      tbody.appendChild(tr);
    });

    const latest = rows[0] || {};
    renderVital('hr', 'hrGauge', latest.heart_rate, 150, 'bpm',
        latest.heart_rate < 55 || latest.heart_rate > 100 ? 'REVIEW' : 'NORMAL',
        latest.heart_rate < 55 || latest.heart_rate > 100 ? 'attention' : '');
    renderVital('spo2', 'spo2Gauge', latest.spo2, 100, '%',
        latest.spo2 < 95 ? 'LOW' : 'NORMAL',
        latest.spo2 < 95 ? 'critical' : '');
    renderVital('temp', 'tempGauge', latest.body_temp, 42, '°C',
        latest.body_temp < 36 || latest.body_temp > 38 ? 'REVIEW' : 'NORMAL',
        latest.body_temp < 36 || latest.body_temp > 38 ? 'attention' : '');
    renderVital('sleep', 'sleepGauge', latest.sleep_hours, 12, 'hrs',
        latest.sleep_hours < 6 ? 'LOW' : 'NORMAL',
        latest.sleep_hours < 6 ? 'attention' : '');
    renderVital('activity', 'activityGauge', latest.activity_minutes, 120, 'min',
        latest.activity_minutes < 20 ? 'LOW' : 'ACTIVE',
        latest.activity_minutes < 20 ? 'attention' : '');
    renderVital('radiation', 'radiationGauge', latest.radiation_mSv, 5, 'mSv', 'TRACKED', '');
  } catch (err) {
      console.error("Gauge error:", err);
  }
}

// ==========================================
// 5. Load Alerts
// ==========================================
async function loadAlerts() {
  try {
    const res = await fetch('/api/alerts');
    if (res.status === 401) return;
    const alerts = await res.json();
    const ul = document.getElementById('alertsList');
    ul.innerHTML = '';
    if (alerts.length === 0) {
      ul.innerHTML = '<li>No alerts. All good! ✅</li>';
      return;
    }
    alerts.forEach(a => {
      const li = document.createElement('li');
      li.className = a.severity;
      li.innerHTML = `<strong>${a.alert_type}</strong> — ${a.message}
                      <small>${a.created_at}</small>`;
      ul.appendChild(li);
    });
  } catch (err) {}
}

// ==========================================
// 6. Load Recommendation
// ==========================================
async function loadRecommendation() {
  try {
    const res = await fetch('/api/recommendation');
    if (res.status === 401) return;
    const data = await res.json();
    document.getElementById('recommendation').textContent = data.recommendation;
  } catch (err) {}
}

// ==========================================
// 7. Load AI Forecast
// ==========================================
async function loadForecast() {
    try {
        const res = await fetch('/api/forecast');
        if (res.status === 401) return;
        const data = await res.json();

        const widget = document.getElementById('forecastWidget');
        const statusEl = document.getElementById('forecastStatus');
        const msgEl = document.getElementById('forecastMessage');

        if (widget) {
            widget.style.borderLeftColor = data.color;
            statusEl.innerText = `Forecast: ${data.status}`;
            statusEl.style.color = data.color;
            msgEl.innerText = data.message;
        }
    } catch (err) {
        console.error("Forecast error:", err);
    }
}

// ==========================================
// 8. Form Submission
// ==========================================
document.getElementById('healthForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  const btn = e.target.querySelector('button[type="submit"]');
  const originalText = btn.innerText;
  btn.innerText = "Analyzing...";
  btn.disabled = true;

  const payload = {
    heart_rate: parseInt(document.getElementById('heart_rate').value) || 0,
    systolic_bp: parseInt(document.getElementById('systolic_bp').value) || 0,
    diastolic_bp: parseInt(document.getElementById('diastolic_bp').value) || 0,
    spo2: parseInt(document.getElementById('spo2').value) || 0,
    body_temp: parseFloat(document.getElementById('body_temp').value) || 0,
    sleep_hours: parseFloat(document.getElementById('sleep_hours').value) || 0,
    activity_minutes: parseInt(document.getElementById('activity_minutes').value) || 0,
    radiation_mSv: parseFloat(document.getElementById('radiation_mSv').value) || 0
  };

  try {
    const res = await fetch('/api/health/submit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    
    if (res.status === 401) { window.location.href = '/login'; return; }
    
    const data = await res.json();

    const resultEl = document.getElementById('result');
    resultEl.className = 'result ' + data.risk_status.toLowerCase().replace(' ', '-');
    resultEl.textContent = `Risk Status: ${data.risk_status} (confidence ${data.confidence}%)`;

    if (!simInterval) {
        document.getElementById('healthForm').reset();
    }

    loadHistory();
    loadAlerts();
    loadRecommendation();
    loadForecast();
  } catch (err) {
    console.error('Submission error:', err);
  } finally {
    btn.innerText = originalText;
    btn.disabled = false;
  }
});

// ==========================================
// 9. Live Simulation Logic
// ==========================================
let simInterval = null;

function toggleSimulation() {
    const btn = document.getElementById('simBtn');
    if (simInterval) {
        clearInterval(simInterval);
        simInterval = null;
        btn.innerText = "▶ Start Live Simulation";
        btn.style.background = "#e67e22";
    } else {
        btn.innerText = "⏹ Stop Simulation";
        btn.style.background = "#c0392b";
        
        simInterval = setInterval(() => {
            const randomHR = Math.floor(Math.random() * 35) + 60;
            const randomSys = Math.floor(Math.random() * 25) + 110;
            const randomDia = Math.floor(Math.random() * 15) + 70;
            const randomSpo2 = Math.floor(Math.random() * 6) + 93;
            const randomTemp = (Math.random() * 1.5 + 36.3).toFixed(1);
            const randomRad = (Math.random() * 2 + 0.1).toFixed(2);
            
            document.getElementById('heart_rate').value = randomHR;
            document.getElementById('systolic_bp').value = randomSys;
            document.getElementById('diastolic_bp').value = randomDia;
            document.getElementById('spo2').value = randomSpo2;
            document.getElementById('body_temp').value = randomTemp;
            document.getElementById('sleep_hours').value = "7.5";
            document.getElementById('activity_minutes').value = "45";
            document.getElementById('radiation_mSv').value = randomRad;
            
            document.getElementById('healthForm').dispatchEvent(new Event('submit'));
        }, 4000); 
    }
}

// ==========================================
// 10. AI Chatbot Logic
// ==========================================
const chatHistory = [];

function toggleChat() {
    const box = document.getElementById('chatBox');
    box.style.display = box.style.display === 'flex' ? 'none' : 'flex';
}

function handleChatEnter(e) {
    if (e.key === 'Enter') sendChatMessage();
}

async function sendChatMessage() {
    const input = document.getElementById('chatInput');
    const message = input.value.trim();
    if (!message) return;

    addMessage(message, 'user');
    input.value = '';

    const typingId = 'typing-' + Date.now();
    const msgContainer = document.getElementById('chatMessages');
    const typingDiv = document.createElement('div');
    typingDiv.className = 'msg ai';
    typingDiv.id = typingId;
    typingDiv.innerText = 'Typing...';
    msgContainer.appendChild(typingDiv);
    msgContainer.scrollTop = msgContainer.scrollHeight;

    try {
        const res = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: message, history: chatHistory.slice(-10) })
        });
        const data = await res.json();
        
        const typingEl = document.getElementById(typingId);
        if (typingEl) typingEl.remove();
        
        if (!res.ok) {
            addMessage(data.error || 'AstroDoc is temporarily unavailable. Please try again.', 'ai');
        } else if (data.reply) {
            addMessage(data.reply, 'ai');
            chatHistory.push(
                { role: 'user', content: message },
                { role: 'assistant', content: data.reply }
            );
        } else {
            addMessage("Sorry, I couldn't process that.", 'ai');
        }
    } catch (err) {
        const typingEl = document.getElementById(typingId);
        if (typingEl) typingEl.remove();
        addMessage("Error connecting to AI. Please try again.", 'ai');
    }
}

function addMessage(text, sender) {
    const container = document.getElementById('chatMessages');
    const div = document.createElement('div');
    div.className = `msg ${sender}`;
    div.innerText = text;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
}

// ==========================================
// 11. Initialization
// ==========================================
loadHistory();
loadAlerts();
loadRecommendation();
loadForecast();

setInterval(() => {
  loadHistory();
  loadAlerts();
  loadRecommendation();
}, 10000);

setInterval(loadForecast, 15000);
// ==========================================
// 12. LOSS OF SIGNAL (LOS) SIMULATOR
// ==========================================
let isLOSActive = false;

function toggleLOS() {
    const banner = document.getElementById('losBanner');
    const toggleBtn = document.getElementById('losToggle');
    
    if (!isLOSActive) {
        // Enable LOS
        isLOSActive = true;
        banner.classList.add('active');
        document.body.classList.add('los-blackout');
        toggleBtn.classList.add('active');
        toggleBtn.innerText = "📡 Signal: OFFLINE";
    } else {
        // Disable LOS
        isLOSActive = false;
        banner.classList.remove('active');
        document.body.classList.remove('los-blackout');
        toggleBtn.classList.remove('active');
        toggleBtn.innerText = "📡 Signal: ONLINE";
        
        // Sync cached data when signal returns
        syncCachedData();
    }
}

// Override the form submission to cache if LOS is active
const originalSubmit = document.getElementById('healthForm').onsubmit;

document.getElementById('healthForm').addEventListener('submit', async (e) => {
    // If LOS is active, prevent the default network submit
    if (isLOSActive) {
        e.preventDefault();
        e.stopImmediatePropagation(); // Stop the other listener from firing
        
        const payload = {
            heart_rate: parseInt(document.getElementById('heart_rate').value) || 0,
            systolic_bp: parseInt(document.getElementById('systolic_bp').value) || 0,
            diastolic_bp: parseInt(document.getElementById('diastolic_bp').value) || 0,
            spo2: parseInt(document.getElementById('spo2').value) || 0,
            body_temp: parseFloat(document.getElementById('body_temp').value) || 0,
            sleep_hours: parseFloat(document.getElementById('sleep_hours').value) || 0,
            activity_minutes: parseInt(document.getElementById('activity_minutes').value) || 0,
            radiation_mSv: parseFloat(document.getElementById('radiation_mSv').value) || 0
        };

        // Save to LocalStorage
        let cache = JSON.parse(localStorage.getItem('los_cache') || '[]');
        cache.push(payload);
        localStorage.setItem('los_cache', JSON.stringify(cache));

        // Show fake success UI
        const resultEl = document.getElementById('result');
        resultEl.className = 'result at-risk';
        resultEl.textContent = `⚠️ Data Cached Locally. Will sync when signal returns.`;
        
        // Reset form
        document.getElementById('healthForm').reset();
    }
}, true); // Use capturing phase to intercept before the main listener

async function syncCachedData() {
    const cache = JSON.parse(localStorage.getItem('los_cache') || '[]');
    if (cache.length === 0) return;

    console.log(`Syncing ${cache.length} cached records...`);
    
    for (const payload of cache) {
        try {
            await fetch('/api/health/submit', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
        } catch (err) {
            console.error("Failed to sync a record", err);
        }
    }
    
    // Clear cache after successful sync
    localStorage.removeItem('los_cache');
    alert(`📡 Signal Restored! Successfully synced ${cache.length} cached health records to Mission Control.`);
    
    // Refresh the UI
    loadHistory();
    loadAlerts();
    loadRecommendation();
    loadForecast();
}