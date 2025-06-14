document.addEventListener('DOMContentLoaded', () => {
  const grid       = document.getElementById('batch-items-grid');
  const addBtn     = document.getElementById('add-batch-item');
  const templateEl = document.getElementById('empty-batch-item-template');
  const tmplHtml   = templateEl.outerHTML; // pega o <tr> inteiro
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

  // remover linha delegadamente
  grid.addEventListener('click', e => {
    if (e.target.matches('.remove-row')) {
      e.target.closest('.item-row').remove();
      updateIndices();
    }
  });

  // adicionar nova linha
  addBtn.addEventListener('click', () => {
    const formIdx = parseInt(totalForms.value, 10);
    let newRowHtml = tmplHtml
      .replace(/__prefix__/g, formIdx)
      .replace(/ id="empty-batch-item-template"/, '');
    grid.insertAdjacentHTML('beforeend', newRowHtml);
    updateIndices();
  });
});
