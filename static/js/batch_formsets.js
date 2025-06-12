
document.addEventListener('DOMContentLoaded', () => {
  const grid       = document.getElementById('batch-items-grid');
  const addBtn     = document.getElementById('add-batch-item');
  const tmpl       = document.getElementById('empty-form-template').innerHTML;
  const totalForms = document.querySelector('input[name$="-TOTAL_FORMS"]');

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

  grid.addEventListener('click', e => {
    if (e.target.matches('.remove-row')) {
      e.target.closest('.item-row').remove();
      updateIndices();
    }
  });

  addBtn.addEventListener('click', () => {
    const idx    = parseInt(totalForms.value, 10);
    const html   = tmpl.replace(/__prefix__/g, idx);
    grid.insertAdjacentHTML('beforeend', html);
    updateIndices();
  });
});