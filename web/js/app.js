let triageCounter = 0;

document.getElementById('triageConfig').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const logContainer = document.getElementById('logContainer');
    const addLog = (cat, msg) => {
        // Only show Triage, Logic, and Warnings to the client
        const allowed = ['TRIAGE', 'LOGIC', 'WARN'];
        if (!allowed.includes(cat)) return;

        const entry = document.createElement('div');
        entry.className = 'log-entry';
        const time = new Date().toLocaleTimeString();
        entry.innerHTML = `<span class="log-time">${time}</span><span class="log-cat">[${cat}]</span><span>${msg}</span>`;
        logContainer.appendChild(entry); // Chronological order
        logContainer.scrollTop = logContainer.scrollHeight; // Auto-scroll to bottom
    };

    addLog('SYSTEM', 'Attempting to apply ruleset and start triage cycle...');

    const payload = {
        imap_server: document.getElementById('imapServer').value,
        email_user: document.getElementById('emailUser').value,
        email_pass: document.getElementById('emailPass').value,
        msg_provider: document.getElementById('msgProvider').value,
        msg_url: document.getElementById('msgUrl').value,
        vips: document.getElementById('vips').value,
        goal: document.getElementById('goalBox').value,
        urgency: document.getElementById('urgencyBox').value,
        tone: document.getElementById('toneSelect').value,
        enable_filing: document.getElementById('enableFiling').checked,
        enable_flagging: document.getElementById('enableFlagging').checked
    };

    try {
        const response = await fetch('/api/triage', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        
        const data = await response.json();
        
        if (data.status === 'simulation') {
            addLog('WARN', 'Credentials not provided. Running in Demo/Simulation mode.');
        }

        data.results.forEach(res => {
            triageCounter++;
            const triage = res.triage;
            const mail = res.mail;
            addLog('TRIAGE', `<b>[#${triageCounter}]</b> Decided: ${triage.category} (P:${triage.priority}) for "${mail.subject}" from ${mail.from}`);
            addLog('LOGIC', `Rationale: ${triage.rationale}`);
        });

        addLog('SYSTEM', 'Triage cycle complete.');

    } catch (err) {
        addLog('ERROR', `Connection failed: ${err.message}`);
    }
});

// Handle Connection Testing
document.getElementById('testConnBtn').addEventListener('click', async () => {
    const testStatus = document.getElementById('testStatus');
    testStatus.textContent = " Checking...";
    testStatus.style.color = "var(--text-main)";

    const payload = {
        imap_server: document.getElementById('imapServer').value,
        email_user: document.getElementById('emailUser').value,
        email_pass: document.getElementById('emailPass').value
    };

    try {
        const resp = await fetch('/api/test_connection', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await resp.json();
        
        if (data.status === 'success') {
            testStatus.textContent = " " + data.message;
            testStatus.style.color = "#145A5A";
        } else {
            testStatus.textContent = " " + data.message;
            testStatus.style.color = "#d9534f";
        }
    } catch (e) {
        testStatus.textContent = " Error reaching server.";
        testStatus.style.color = "#d9534f";
    }
});
