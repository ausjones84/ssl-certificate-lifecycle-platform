// dashboard/dashboard.js - Certificate Lifecycle Dashboard Logic

let allCertificates = [];

async function loadInventory() {
  document.getElementById('last-updated').textContent = 'Loading...';
  
  try {
    // Try to load from reports/CertificateInventory.json
    const response = await fetch('../reports/CertificateInventory.json');
    if (!response.ok) throw new Error('Inventory file not found');
    const data = await response.json();
    allCertificates = data.certificates || [];
    renderDashboard(data);
    document.getElementById('last-updated').textContent = 'Last updated: ' + new Date().toLocaleString();
  } catch (e) {
    // Load demo data for testing
    allCertificates = getDemoData();
    renderDashboard({ certificates: allCertificates, generated: new Date().toISOString() });
    document.getElementById('last-updated').textContent = 'Demo data (run discover to load real data)';
  }
}

function renderDashboard(data) {
  const certs = data.certificates || [];
  
  // Count by risk
  const expired = certs.filter(c => c.risk_level === 'EXPIRED').length;
  const crit30 = certs.filter(c => ['EXPIRED','CRITICAL'].includes(c.risk_level)).length;
  const high60 = certs.filter(c => ['EXPIRED','CRITICAL','HIGH'].includes(c.risk_level)).length;
  const med90 = certs.filter(c => ['EXPIRED','CRITICAL','HIGH','MEDIUM'].includes(c.risk_level)).length;
  const ok = certs.filter(c => ['LOW','OK'].includes(c.risk_level)).length;
  
  document.getElementById('count-expired').textContent = expired;
  document.getElementById('count-30').textContent = crit30;
  document.getElementById('count-60').textContent = high60;
  document.getElementById('count-90').textContent = med90;
  document.getElementById('count-ok').textContent = ok;
  document.getElementById('count-total').textContent = certs.length;
  
  // Action required table
  const actionCerts = certs.filter(c => ['EXPIRED','CRITICAL','HIGH'].includes(c.risk_level))
    .sort((a,b) => (a.days_until_expiry || 9999) - (b.days_until_expiry || 9999));
  
  if (actionCerts.length > 0) {
    document.getElementById('action-empty').style.display = 'none';
    document.getElementById('table-action').style.display = 'table';
    document.getElementById('body-action').innerHTML = actionCerts.map(renderRow).join('');
  }
  
  // Full inventory
  if (certs.length > 0) {
    document.getElementById('inventory-empty').style.display = 'none';
    document.getElementById('table-inventory').style.display = 'table';
    document.getElementById('body-inventory').innerHTML = 
      certs.sort((a,b) => (a.days_until_expiry||9999) - (b.days_until_expiry||9999)).map(renderFullRow).join('');
  }
}

function renderRow(c) {
  const days = c.days_until_expiry;
  const daysClass = days < 0 ? 'days-critical' : days <= 30 ? 'days-critical' : days <= 60 ? 'days-high' : 'days-medium';
  return `<tr>
    <td>${c.domain || '-'}</td>
    <td>${c.cert_name || '-'}</td>
    <td>${c.key_vault || '-'}</td>
    <td>${c.app_service || '-'}</td>
    <td>${c.expiration || '-'}</td>
    <td class="${daysClass}">${days !== null ? days : '?'}</td>
    <td><span class="badge badge-${c.risk_level}">${c.risk_level}</span></td>
  </tr>`;
}

function renderFullRow(c) {
  const days = c.days_until_expiry;
  const daysClass = days < 0 ? 'days-critical' : days <= 30 ? 'days-critical' : days <= 60 ? 'days-high' : days <= 90 ? 'days-medium' : 'days-ok';
  return `<tr>
    <td>${c.domain || '-'}</td>
    <td>${c.cert_name || '-'}</td>
    <td>${c.key_vault || '-'}</td>
    <td>${c.app_service || '-'}</td>
    <td>${c.expiration || '-'}</td>
    <td class="${daysClass}">${days !== null ? days : '?'}</td>
    <td><span class="badge badge-${c.risk_level}">${c.risk_level}</span></td>
    <td>${c.binding_status || '-'}</td>
  </tr>`;
}

function filterTable() {
  const search = document.getElementById('search-input').value.toLowerCase();
  const riskFilter = document.getElementById('risk-filter').value;
  
  const filtered = allCertificates.filter(c => {
    const matchSearch = !search || 
      (c.cert_name || '').toLowerCase().includes(search) ||
      (c.domain || '').toLowerCase().includes(search) ||
      (c.key_vault || '').toLowerCase().includes(search) ||
      (c.app_service || '').toLowerCase().includes(search);
    const matchRisk = !riskFilter || c.risk_level === riskFilter;
    return matchSearch && matchRisk;
  });
  
  document.getElementById('body-inventory').innerHTML = 
    filtered.sort((a,b) => (a.days_until_expiry||9999) - (b.days_until_expiry||9999)).map(renderFullRow).join('');
  
  if (filtered.length === 0) {
    document.getElementById('table-inventory').style.display = 'none';
    document.getElementById('inventory-empty').style.display = 'block';
    document.getElementById('inventory-empty').textContent = 'No certificates match your filter.';
  } else {
    document.getElementById('table-inventory').style.display = 'table';
    document.getElementById('inventory-empty').style.display = 'none';
  }
}

function getDemoData() {
  const today = new Date();
  function daysFrom(d) { return new Date(today.getTime() + d * 86400000).toISOString().split('T')[0]; }
  return [
    { cert_name: 'king-wildcard', domain: '*.king5.com', key_vault: 'tgna-kv-king-ctrl', app_service: 'interactive-king5', expiration: daysFrom(4), days_until_expiry: 4, risk_level: 'CRITICAL', binding_status: 'BOUND' },
    { cert_name: 'komo-wildcard', domain: '*.komo.tv', key_vault: 'tgna-kv-komo-ctrl', app_service: 'interactive-komo', expiration: daysFrom(25), days_until_expiry: 25, risk_level: 'HIGH', binding_status: 'BOUND' },
    { cert_name: 'king5-api', domain: 'api.king5.com', key_vault: 'tgna-kv-king-ctrl', app_service: 'king5-api', expiration: daysFrom(55), days_until_expiry: 55, risk_level: 'MEDIUM', binding_status: 'BOUND' },
    { cert_name: 'tegna-corp', domain: '*.tegna.com', key_vault: 'tgna-kv-corp', app_service: 'corp-web', expiration: daysFrom(180), days_until_expiry: 180, risk_level: 'OK', binding_status: 'BOUND' },
  ];
}

// Auto-load on page open
document.addEventListener('DOMContentLoaded', loadInventory);
