/*
 Patient Identity UI helper
 - Duplicate detection while typing registration details
 - Search by UHID / name / phone
 - Works with /patients/* compatibility APIs
*/
(function () {
  const csrf = document.querySelector('meta[name="csrf-token"]')?.content || '';

  async function api(url, method = 'GET', payload = null) {
    const opts = {
      method,
      headers: {
        'Accept': 'application/json',
        'X-CSRFToken': csrf
      },
      credentials: 'include'
    };
    if (payload) {
      opts.headers['Content-Type'] = 'application/json';
      opts.body = JSON.stringify(payload);
    }
    const res = await fetch(url, opts);
    const data = await res.json();
    return { ok: res.ok, status: res.status, data };
  }

  function readRegistrationFields() {
    return {
      name: (document.getElementById('pi_name')?.value || '').trim(),
      age: (document.getElementById('pi_age')?.value || '').trim(),
      gender: (document.getElementById('pi_gender')?.value || '').trim(),
      phone: (document.getElementById('pi_phone')?.value || '').trim(),
      address: (document.getElementById('pi_address')?.value || '').trim()
    };
  }

  function renderDuplicates(duplicates) {
    const box = document.getElementById('pi_duplicates');
    if (!box) return;
    if (!duplicates || !duplicates.length) {
      box.innerHTML = '';
      box.style.display = 'none';
      return;
    }
    box.style.display = 'block';
    box.innerHTML = `
      <div class="alert alert-warning mb-2">
        <strong>Possible existing patient found</strong>
      </div>
      ${duplicates.map(d => `
        <div class="border rounded p-2 mb-2 d-flex justify-content-between align-items-center">
          <div>
            <div><strong>${d.name}</strong></div>
            <div class="small text-muted">UHID: ${d.uhid} | Age: ${d.age || '-'} | Phone: ${d.phone || '-'}</div>
          </div>
          <button class="btn btn-sm btn-outline-primary" type="button" data-patient-id="${d.id}">
            Select Existing
          </button>
        </div>
      `).join('')}
      <button id="pi_force_create" class="btn btn-sm btn-danger" type="button">Create New Anyway</button>
    `;

    box.querySelectorAll('button[data-patient-id]').forEach(btn => {
      btn.addEventListener('click', () => {
        const pid = btn.getAttribute('data-patient-id');
        document.dispatchEvent(new CustomEvent('patient:selected', { detail: { patient_id: parseInt(pid, 10) } }));
      });
    });
    const forceBtn = document.getElementById('pi_force_create');
    if (forceBtn) {
      forceBtn.addEventListener('click', () => submitRegistration(true));
    }
  }

  let dupTimer = null;
  async function checkDuplicatesDebounced() {
    clearTimeout(dupTimer);
    dupTimer = setTimeout(async () => {
      const payload = readRegistrationFields();
      if (!payload.name || !payload.age) return renderDuplicates([]);
      const r = await api('/patients/find-similar', 'POST', {
        name: payload.name,
        age: parseInt(payload.age, 10),
        phone: payload.phone
      });
      if (r.ok && r.data?.similar) {
        renderDuplicates(r.data.similar);
      }
    }, 350);
  }

  async function submitRegistration(forceCreate = false) {
    const payload = readRegistrationFields();
    if (!payload.name || !payload.age || !payload.gender) {
      alert('Name, age, and gender are required');
      return;
    }
    const r = await api('/patients/register', 'POST', {
      ...payload,
      age: parseInt(payload.age, 10),
      force_create: forceCreate
    });
    if (r.ok && r.data?.success) {
      alert(`Registered: ${r.data.patient?.name} | UHID: ${r.data.patient?.uhid}`);
      renderDuplicates([]);
      document.dispatchEvent(new CustomEvent('patient:registered', { detail: r.data.patient }));
      return;
    }
    if (r.status === 409 && r.data?.duplicates) {
      renderDuplicates(r.data.duplicates);
      return;
    }
    alert(r.data?.error || 'Registration failed');
  }

  let searchTimer = null;
  async function searchPatientsDebounced() {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(async () => {
      const q = (document.getElementById('pi_search')?.value || '').trim();
      const out = document.getElementById('pi_search_results');
      if (!out) return;
      if (q.length < 2) {
        out.innerHTML = '';
        return;
      }
      const r = await api(`/patients/search?q=${encodeURIComponent(q)}&limit=15`);
      if (!r.ok || !r.data?.patients) {
        out.innerHTML = '<div class="small text-danger">Search failed</div>';
        return;
      }
      out.innerHTML = r.data.patients.map(p => `
        <button type="button" class="list-group-item list-group-item-action" data-patient-id="${p.id}">
          <div><strong>${p.name}</strong></div>
          <div class="small text-muted">UHID: ${p.uhid} | ${p.phone || '-'} | ${p.age || '-'}y</div>
        </button>
      `).join('');
      out.querySelectorAll('[data-patient-id]').forEach(btn => {
        btn.addEventListener('click', () => {
          const pid = parseInt(btn.getAttribute('data-patient-id'), 10);
          document.dispatchEvent(new CustomEvent('patient:selected', { detail: { patient_id: pid } }));
        });
      });
    }, 250);
  }

  window.PatientIdentityUI = {
    bindRegistration() {
      ['pi_name', 'pi_age', 'pi_phone'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.addEventListener('input', checkDuplicatesDebounced);
      });
      const submit = document.getElementById('pi_register_btn');
      if (submit) submit.addEventListener('click', () => submitRegistration(false));
    },
    bindSearch() {
      const search = document.getElementById('pi_search');
      if (search) search.addEventListener('input', searchPatientsDebounced);
    },
    registerNow: submitRegistration
  };
})();
