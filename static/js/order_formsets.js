document.addEventListener('DOMContentLoaded', () => {
  const grid       = document.getElementById('items-grid');
  const addBtn     = document.getElementById('add-item');
  const templateEl = document.getElementById('empty-form-template');
  const tmplHtml   = templateEl.outerHTML;       // pega <tr …>…</tr>
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

  // remoção delegada
  grid.addEventListener('click', e => {
    if (e.target.matches('.remove-row')) {
      e.target.closest('.item-row').remove();
      updateIndices();
    const form = document.getElementById('order-form')
    form.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }
  });

  // adicionar nova linha
  addBtn.addEventListener('click', () => {
    const formIdx = parseInt(totalForms.value, 10);
    // injeta o índice e remove o id duplicado
    let newRowHtml = tmplHtml
      .replace(/__prefix__/g, formIdx)
      .replace(/ id="empty-form-template"/, '');
    grid.insertAdjacentHTML('beforeend', newRowHtml);
    updateIndices();
  });
});

