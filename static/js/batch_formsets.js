document.addEventListener('DOMContentLoaded', () => {
  const prefix = 'batch_item';
  const form = document.querySelector('form');
  const totalForms = document.querySelector(`[name="${prefix}-TOTAL_FORMS"]`);
  const grid = document.getElementById('items-grid');
  const template = document.getElementById('empty-form-template');
  const addBtn = document.getElementById('add-item');

  function reindex() {
    const rows = Array.from(grid.querySelectorAll('tr.item-row:not(.d-none)'));
    rows.forEach((row, i) => {
      row.querySelectorAll('input, select, textarea, label').forEach(el => {
        if (el.name) el.name = el.name.replace(/batch_item-\d+-/, `batch_item-${i}-`);
        if (el.id)   el.id   = el.id.replace(/id_batch_item-\d+-/, `id_batch_item-${i}-`);
        if (el.htmlFor) el.htmlFor = el.htmlFor.replace(/id_batch_item-\d+-/, `id_batch_item-${i}-`);
      });
    });
    totalForms.value = rows.length;
  }

  addBtn.addEventListener('click', () => {
    const index = parseInt(totalForms.value, 10);
    const newRow = template.cloneNode(true);
    newRow.removeAttribute('id');
    newRow.classList.remove('d-none');
    newRow.innerHTML = newRow.innerHTML
      .replace(/batch_item-__prefix__/g, `batch_item-${index}`)
      .replace(/id_batch_item-__prefix__/g, `id_batch_item-${index}`);
    grid.appendChild(newRow);
    reindex();
  });

  grid.addEventListener('click', e => {
    if (e.target.matches('.remove-row')) {
      e.target.closest('tr').remove();
      reindex();
    }
  });

  form.addEventListener('submit', () => {
    const tpl = document.getElementById('empty-form-template');
    if (tpl) tpl.remove();
  });

  reindex();
});