const API = 'http://localhost:8000';
const ALLOWED_DOMAINS = ['joulestowatts.com', 'joulestowatts.co'];

const EXCEL_ROWS = [
  { key: 'sourcing_date',         label: 'Sourcing Date' },
  { key: null,                    label: 'Sourcing Partner' },
  { key: 'pool_verified',         label: 'Pool Verified (Y/N)' },
  { key: 'name',                  label: 'Name of the Consultant' },
  { key: 'mobile_number',         label: 'Mobile Number' },
  { key: 'email',                 label: 'Email' },
  { key: 'linkedin_url',          label: 'LinkedIn URL' },
  { key: 'education',             label: 'Education Background' },
  { key: 'current_location',      label: 'Current Location' },
  { key: 'profile_active_naukri', label: 'Profile Active in Naukri (Y/N)' },
  { key: 'experience_range',      label: 'Experience Range' },
  { key: 'current_company',       label: 'Current Companies' },
  { key: 'relevant_skills',       label: 'Relevant Skills' },
  { key: 'immediate_joinee',      label: 'Whether Immediate Joinee (Y/N)' },
];

let authToken = null, currentMode = 'text', selectedFiles = [], lastResult = null, verifiedOtp = '';

// ── Screens ────────────────────────────────────────────────────────────────
function showScreen(id) {
  ['screenLogin','screenOtp','screenMain'].forEach(s =>
    document.getElementById(s).classList.toggle('hidden', s !== id)
  );
}

function goToOtpStep(n) {
  [1,2,3].forEach(i => {
    document.getElementById(`otpStep${i}`).classList.toggle('hidden', i !== n);
    const dot = document.getElementById(`si${i}`);
    const line = document.getElementById(`sl${i}`);
    dot.classList.remove('active','done');
    if (i < n)  dot.classList.add('done');
    if (i === n) dot.classList.add('active');
    if (line) line.classList.toggle('done', i < n);
  });
}

// ── Domain validation ──────────────────────────────────────────────────────
function validateEmailDomain(inputEl, hintEl) {
  const val = inputEl.value.trim(), atIdx = val.indexOf('@');
  if (atIdx === -1 || !val.slice(atIdx+1).includes('.')) {
    inputEl.classList.remove('input-valid','input-invalid');
    hintEl.textContent = ''; hintEl.className = 'domain-hint'; return false;
  }
  const domain = val.slice(atIdx+1).toLowerCase();
  const ok = ALLOWED_DOMAINS.includes(domain);
  inputEl.classList.toggle('input-valid', ok);
  inputEl.classList.toggle('input-invalid', !ok);
  hintEl.className   = `domain-hint ${ok ? 'valid' : 'invalid'}`;
  hintEl.textContent = ok ? '✓ Allowed domain' : '✗ Only @joulestowatts.com or @joulestowatts.co';
  return ok;
}

function wireEmailValidation(inputId, hintId, btnId) {
  const input = document.getElementById(inputId);
  const hint  = document.getElementById(hintId);
  const btn   = document.getElementById(btnId);
  input.addEventListener('input', () => {
    const ok = validateEmailDomain(input, hint);
    const hasDot = input.value.includes('@') && input.value.slice(input.value.indexOf('@')+1).includes('.');
    if (hasDot) btn.disabled = !ok; else btn.disabled = false;
  });
  input.addEventListener('blur', () => { if (input.value.includes('@')) validateEmailDomain(input, hint); });
}
wireEmailValidation('loginEmail', 'loginEmailHint', 'loginBtn');
wireEmailValidation('otpEmail',   'otpEmailHint',   'sendOtpBtn');

// ── Eye toggles ────────────────────────────────────────────────────────────
function wireEye(btnId, inputId, onId, offId) {
  document.getElementById(btnId).addEventListener('click', () => {
    const input = document.getElementById(inputId);
    const show  = input.type === 'password';
    input.type  = show ? 'text' : 'password';
    document.getElementById(onId).classList.toggle('hidden', show);
    document.getElementById(offId).classList.toggle('hidden', !show);
  });
}
wireEye('toggleLoginPass', 'loginPassword',      'eyeLoginOn',  'eyeLoginOff');
wireEye('toggleOtpPass1',  'otpPassword',        'eyeOtp1On',   'eyeOtp1Off');
wireEye('toggleOtpPass2',  'otpConfirmPassword', 'eyeOtp2On',   'eyeOtp2Off');

// ── OTP boxes ──────────────────────────────────────────────────────────────
const otpBoxEls = () => [...document.querySelectorAll('.otp-box')];
const getOtpValue = () => otpBoxEls().map(b => b.value).join('');

function resetOtpBoxes() {
  otpBoxEls().forEach(b => { b.value = ''; b.classList.remove('filled'); });
  document.getElementById('verifyOtpBtn').disabled = true;
}

document.getElementById('otpBoxes').addEventListener('input', e => {
  const boxes = otpBoxEls(), idx = boxes.indexOf(e.target);
  const val = e.target.value.replace(/\D/g, '');
  e.target.value = val.slice(-1);
  e.target.classList.toggle('filled', !!e.target.value);
  if (val && idx < boxes.length - 1) boxes[idx + 1].focus();
  document.getElementById('verifyOtpBtn').disabled = getOtpValue().length < 6;
});

document.getElementById('otpBoxes').addEventListener('keydown', e => {
  const boxes = otpBoxEls(), idx = boxes.indexOf(e.target);
  if (e.key === 'Backspace' && !e.target.value && idx > 0) {
    boxes[idx-1].focus(); boxes[idx-1].value = ''; boxes[idx-1].classList.remove('filled');
  }
  if (e.key === 'ArrowLeft'  && idx > 0)               boxes[idx-1].focus();
  if (e.key === 'ArrowRight' && idx < boxes.length - 1) boxes[idx+1].focus();
});

document.getElementById('otpBoxes').addEventListener('paste', e => {
  e.preventDefault();
  const digits = e.clipboardData.getData('text').replace(/\D/g, '').slice(0, 6);
  const boxes  = otpBoxEls();
  digits.split('').forEach((d, i) => { if (boxes[i]) { boxes[i].value = d; boxes[i].classList.toggle('filled', !!d); } });
  document.getElementById('verifyOtpBtn').disabled = getOtpValue().length < 6;
  if (digits.length === 6) document.getElementById('verifyOtpBtn').focus();
});

// ── Password match ─────────────────────────────────────────────────────────
function checkPasswordMatch() {
  const p1 = document.getElementById('otpPassword').value;
  const p2 = document.getElementById('otpConfirmPassword').value;
  const hint = document.getElementById('matchHint');
  const btn  = document.getElementById('setPasswordBtn');
  if (!p2) { hint.className = 'match-hint hidden'; btn.disabled = true; return; }
  const match = p1 === p2 && p1.length >= 6;
  hint.className   = `match-hint ${match ? 'match' : 'nomatch'}`;
  hint.textContent = match ? '✓ Passwords match' : p1 !== p2 ? '✗ Passwords do not match' : '✗ Min 6 characters';
  btn.disabled     = !match;
}
document.getElementById('otpPassword').addEventListener('input', checkPasswordMatch);
document.getElementById('otpConfirmPassword').addEventListener('input', checkPasswordMatch);

// ── Bootstrap ──────────────────────────────────────────────────────────────
chrome.storage.local.get(['authToken','userEmail','savedText','savedMode','savedResult'], async store => {
  if (store.authToken) {
    try {
      const res = await fetch(`${API}/auth/me`, { headers: { Authorization: `Bearer ${store.authToken}` }, signal: AbortSignal.timeout(4000) });
      if (res.ok) {
        authToken = store.authToken;
        document.getElementById('userEmailLabel').textContent = store.userEmail || '';
        if (store.savedMode)   switchTab(store.savedMode);
        if (store.savedText)   document.getElementById('textArea').value = store.savedText;
        if (store.savedResult) { lastResult = store.savedResult; renderResults(lastResult); document.getElementById('results').classList.remove('hidden'); }
        showScreen('screenMain'); checkHealth(); return;
      }
    } catch { /**/ }
  }
  showScreen('screenLogin');
});

async function checkHealth() {
  const dot = document.getElementById('statusDot'), label = document.getElementById('statusLabel');
  try {
    const r = await fetch(`${API}/health`, { signal: AbortSignal.timeout(3000) });
    if (r.ok) { dot.className = 'status-dot online'; label.textContent = 'API ready'; return; }
  } catch { /**/ }
  dot.className = 'status-dot offline'; label.textContent = 'API offline';
}

// ── Login ──────────────────────────────────────────────────────────────────
document.getElementById('loginBtn').addEventListener('click', async () => {
  const email = document.getElementById('loginEmail').value.trim();
  const password = document.getElementById('loginPassword').value;
  clearAuthError('loginError');
  if (!email || !password) return showAuthError('loginError', 'Enter email and password.');
  if (!ALLOWED_DOMAINS.includes(email.split('@')[1]?.toLowerCase())) return showAuthError('loginError', 'Only @joulestowatts.com or @joulestowatts.co allowed.');
  setAuthLoading('loginBtn','loginBtnLabel','loginSpinner', true, 'Signing in…');
  try {
    const res = await fetch(`${API}/auth/login`, { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({email, password}) });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Login failed');
    await onLoginSuccess(data.token, data.email);
  } catch(e) { showAuthError('loginError', e.message); }
  finally { setAuthLoading('loginBtn','loginBtnLabel','loginSpinner', false, 'Sign in'); }
});

document.getElementById('goToOtp').addEventListener('click', () => { clearAuthError('loginError'); goToOtpStep(1); showScreen('screenOtp'); });
document.getElementById('goToLogin').addEventListener('click', () => { showScreen('screenLogin'); });

// ── OTP Step 1 ─────────────────────────────────────────────────────────────
document.getElementById('sendOtpBtn').addEventListener('click', async () => {
  const email = document.getElementById('otpEmail').value.trim();
  clearAuthError('sendOtpError');
  if (!email) return showAuthError('sendOtpError', 'Enter your email.');
  if (!ALLOWED_DOMAINS.includes(email.split('@')[1]?.toLowerCase())) return showAuthError('sendOtpError', 'Only @joulestowatts.com or @joulestowatts.co allowed.');
  setAuthLoading('sendOtpBtn','sendOtpLabel','sendOtpSpinner', true, 'Sending…');
  try {
    const res = await fetch(`${API}/auth/request-otp`, { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({email}) });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Failed to send OTP');
    document.getElementById('otpSentTo').textContent = email;
    resetOtpBoxes(); goToOtpStep(2);
    setTimeout(() => otpBoxEls()[0]?.focus(), 100);
  } catch(e) { showAuthError('sendOtpError', e.message); }
  finally { setAuthLoading('sendOtpBtn','sendOtpLabel','sendOtpSpinner', false, 'Send OTP'); }
});

// ── OTP Step 2 ─────────────────────────────────────────────────────────────
document.getElementById('verifyOtpBtn').addEventListener('click', async () => {
  const email = document.getElementById('otpEmail').value.trim();
  const otp   = getOtpValue();
  clearAuthError('otpVerifyError');
  setAuthLoading('verifyOtpBtn','verifyOtpLabel','verifyOtpSpinner', true, 'Verifying…');
  try {
    const res = await fetch(`${API}/auth/check-otp`, { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({email, otp}) });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Invalid OTP');
    verifiedOtp = otp;
    document.getElementById('otpPassword').value = '';
    document.getElementById('otpConfirmPassword').value = '';
    document.getElementById('matchHint').className = 'match-hint hidden';
    document.getElementById('setPasswordBtn').disabled = true;
    goToOtpStep(3);
    setTimeout(() => document.getElementById('otpPassword').focus(), 100);
  } catch(e) {
    showAuthError('otpVerifyError', e.message);
    const boxes = document.getElementById('otpBoxes');
    boxes.style.animation = 'none';
    requestAnimationFrame(() => { boxes.style.animation = 'shake .35s ease'; });
  }
  finally { setAuthLoading('verifyOtpBtn','verifyOtpLabel','verifyOtpSpinner', false, 'Verify OTP'); }
});

document.getElementById('resendOtp').addEventListener('click', () => { clearAuthError('otpVerifyError'); goToOtpStep(1); });

// ── OTP Step 3 ─────────────────────────────────────────────────────────────
document.getElementById('setPasswordBtn').addEventListener('click', async () => {
  const email    = document.getElementById('otpEmail').value.trim();
  const password = document.getElementById('otpPassword').value;
  clearAuthError('setPassError');
  setAuthLoading('setPasswordBtn','setPassLabel','setPassSpinner', true, 'Setting up…');
  try {
    const res = await fetch(`${API}/auth/verify-otp`, { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({email, otp:verifiedOtp, password}) });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Failed to set password');
    await onLoginSuccess(data.token, data.email);
  } catch(e) { showAuthError('setPassError', e.message); }
  finally { setAuthLoading('setPasswordBtn','setPassLabel','setPassSpinner', false, 'Set Password & Sign in'); }
});

async function onLoginSuccess(token, email) {
  authToken = token;
  await chrome.storage.local.set({ authToken: token, userEmail: email });
  document.getElementById('userEmailLabel').textContent = email;
  showScreen('screenMain'); checkHealth();
}

// ── Logout ─────────────────────────────────────────────────────────────────
document.getElementById('logoutBtn').addEventListener('click', () => {
  authToken = null; lastResult = null; selectedFiles = [];
  chrome.storage.local.remove(['authToken','userEmail','savedText','savedMode','savedResult']);
  document.getElementById('textArea').value = '';
  document.getElementById('fileList').innerHTML = '';
  document.getElementById('results').classList.add('hidden');
  document.getElementById('resultGrid').innerHTML = '';
  showScreen('screenLogin');
});

// ── Tabs ───────────────────────────────────────────────────────────────────
function switchTab(mode) {
  currentMode = mode;
  document.getElementById('tabText').classList.toggle('active',    mode === 'text');
  document.getElementById('tabImage').classList.toggle('active',   mode === 'image');
  document.getElementById('panelText').classList.toggle('hidden',  mode !== 'text');
  document.getElementById('panelImage').classList.toggle('hidden', mode !== 'image');
}
document.getElementById('tabText').addEventListener('click',  () => { switchTab('text');  saveState(); });
document.getElementById('tabImage').addEventListener('click', () => { switchTab('image'); saveState(); });

// ── Files ──────────────────────────────────────────────────────────────────
function addFiles(files) {
  for (const f of files) if (!selectedFiles.find(x => x.name===f.name && x.size===f.size)) selectedFiles.push(f);
  renderFileList();
}
function renderFileList() {
  const ul = document.getElementById('fileList'); ul.innerHTML = '';
  selectedFiles.forEach((f, i) => {
    const li = document.createElement('li'); li.className = 'file-item';
    li.innerHTML = `<svg class="file-item-icon" width="14" height="14" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M4 3a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V7.414A2 2 0 0017.414 6L14 2.586A2 2 0 0012.586 2H6a2 2 0 00-2 2zm8 0v4h4l-4-4z" clip-rule="evenodd"/></svg><span class="file-item-name" title="${f.name}">${f.name}</span><button class="file-item-remove" data-i="${i}">&#215;</button>`;
    ul.appendChild(li);
  });
  ul.querySelectorAll('.file-item-remove').forEach(btn => btn.addEventListener('click', () => { selectedFiles.splice(+btn.dataset.i, 1); renderFileList(); }));
}
const dropZone = document.getElementById('dropZone'), fileInput = document.getElementById('fileInput');
dropZone.addEventListener('click', () => fileInput.click());
document.getElementById('browseLink').addEventListener('click', e => { e.stopPropagation(); fileInput.click(); });
fileInput.addEventListener('change', () => { addFiles(fileInput.files); fileInput.value = ''; });
dropZone.addEventListener('dragover', e => { e.preventDefault(); dropZone.classList.add('drag-over'); });
dropZone.addEventListener('dragleave', () => dropZone.classList.remove('drag-over'));
dropZone.addEventListener('drop', e => { e.preventDefault(); dropZone.classList.remove('drag-over'); addFiles(e.dataTransfer.files); });

// ── Extract ────────────────────────────────────────────────────────────────
document.getElementById('extractBtn').addEventListener('click', extract);
async function extract() {
  hideError();
  const text = document.getElementById('textArea').value.trim();
  if (currentMode==='text'  && !text)                return showError('Please enter some profile text.');
  if (currentMode==='image' && !selectedFiles.length) return showError('Please add at least one image.');
  setLoading(true);
  try {
    const fd = new FormData();
    if (currentMode === 'text') { fd.append('text', text); } else { for (const f of selectedFiles) fd.append('images', f); }
    const res = await fetch(`${API}/extract`, { method:'POST', headers:{Authorization:`Bearer ${authToken}`}, body:fd });
    if (res.status === 401) { showError('Session expired. Please sign in again.'); return; }
    if (!res.ok) { const e = await res.json().catch(()=>({})); throw new Error(e.detail||`Error ${res.status}`); }
    lastResult = await res.json(); saveState(); renderResults(lastResult);
    document.getElementById('results').classList.remove('hidden');
  } catch(e) { showError(e.message || 'Extraction failed. Is the API running?'); }
  finally { setLoading(false); }
}

// ── Clear ──────────────────────────────────────────────────────────────────
document.getElementById('clearBtn').addEventListener('click', () => {
  document.getElementById('textArea').value = ''; selectedFiles = []; renderFileList(); lastResult = null;
  document.getElementById('results').classList.add('hidden'); document.getElementById('resultGrid').innerHTML = ''; hideError();
  chrome.storage.local.remove(['savedText','savedResult']);
});

// ── Render results ─────────────────────────────────────────────────────────
function renderResults(data) {
  const grid = document.getElementById('resultGrid'); grid.innerHTML = '';
  EXCEL_ROWS.forEach(({ key, label }) => {
    const val = key ? data[key] : null;
    const row = document.createElement('div'); row.className = 'result-row';
    const lEl = document.createElement('div'); lEl.className = 'result-label'; lEl.textContent = label;
    const vEl = document.createElement('div'); vEl.className = 'result-value';
    if (!key || val===null || val===undefined || String(val).trim()==='') { vEl.classList.add('null-val'); vEl.textContent = '—'; }
    else {
      const v = String(val).trim().toLowerCase();
      if (['yes','no','n/a'].includes(v)) { const b = document.createElement('span'); b.className=`badge ${v==='yes'?'badge-yes':v==='no'?'badge-no':'badge-na'}`; b.textContent=String(val).trim(); vEl.appendChild(b); }
      else { vEl.textContent = val; }
    }
    row.appendChild(lEl); row.appendChild(vEl); grid.appendChild(row);
  });
}

// ── Copy for Excel ─────────────────────────────────────────────────────────
document.getElementById('copyBtn').addEventListener('click', () => {
  if (!lastResult) return;
  const text = EXCEL_ROWS.map(({key}) => { if (!key) return ''; const v = lastResult[key]; return v===null||v===undefined?'':String(v); }).join('\n');
  navigator.clipboard.writeText(text).catch(() => { const ta = Object.assign(document.createElement('textarea'),{value:text,style:'position:fixed;opacity:0'}); document.body.appendChild(ta); ta.select(); document.execCommand('copy'); document.body.removeChild(ta); }).finally(showToast);
});
function showToast() { const t=document.getElementById('copyToast'); t.classList.remove('hidden'); setTimeout(()=>t.classList.add('hidden'),2200); }

// ── Helpers ────────────────────────────────────────────────────────────────
function saveState() { const p={savedMode:currentMode, savedText:document.getElementById('textArea').value}; if (lastResult) p.savedResult=lastResult; chrome.storage.local.set(p); }
document.getElementById('textArea').addEventListener('input', saveState);
function setLoading(on) { document.getElementById('extractBtn').disabled=on; document.getElementById('btnLabel').textContent=on?'Extracting…':'Extract Profile'; document.getElementById('spinner').classList.toggle('hidden',!on); }
function showError(msg) { document.getElementById('errorText').textContent=msg; document.getElementById('errorBanner').classList.remove('hidden'); }
function hideError() { document.getElementById('errorBanner').classList.add('hidden'); }
function showAuthError(id,msg) { const el=document.getElementById(id); el.textContent=msg; el.classList.remove('hidden'); }
function clearAuthError(id) { document.getElementById(id).classList.add('hidden'); }
function setAuthLoading(btnId,labelId,spinnerId,on,label) { document.getElementById(btnId).disabled=on; document.getElementById(labelId).textContent=label; document.getElementById(spinnerId).classList.toggle('hidden',!on); }
