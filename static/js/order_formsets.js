document.addEventListener('DOMContentLoaded', () => {
  const form       = document.getElementById('order-form');
  const grid       = document.getElementById('items-grid');
  const addBtn     = document.getElementById('add-item');
  const importBtn  = document.getElementById('btn-import-items');
  const templateEl = document.getElementById('empty-form-template');
  const totalForms = document.querySelector('input[name$="-TOTAL_FORMS"]');

  if (importBtn) {
    importBtn.addEventListener('click', () => {
      const orderForm = document.getElementById('order-form');
      ['customer','exporter','company'].forEach(name => {
      const el = orderForm.querySelector(`[name="${name}"]`);
      document.getElementById(`import-${name}`).value = el?.value || '';
    });
    document.getElementById('import-form').submit();
    });
  }

  if (grid) {
    ['keydown','keypress'].forEach(evt =>
      grid.addEventListener(evt, e => { if (e.key === 'Enter') e.preventDefault(); }, true)
    );

    grid.addEventListener('click', e => {
      if (e.target.matches('.remove-row')) {
        e.target.closest('.item-row').remove();
        updateIndices();
      }
    });
  }

  if (addBtn) {
    addBtn.addEventListener('click', () => {
      const formIdx  = parseInt(totalForms.value, 10);
      const newRow   = templateEl.outerHTML.replace(/__prefix__/g, formIdx)
                                           .replace(' id="empty-form-template"', '');
      grid.insertAdjacentHTML('beforeend', newRow);
      updateIndices();
    });
  }

  function updateIndices() {
    const rows = grid.querySelectorAll('.item-row');
    rows.forEach((row, idx) => {
      row.querySelectorAll('input, select').forEach(el => {
        el.name = el.name.replace(/-\d+-/, `-${idx}-`);
        if (el.id) el.id = el.id.replace(/-\d+-/, `-${idx}-`);
      });
    });
    totalForms.value = rows.length;
  }
});

