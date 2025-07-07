// static/js/order_formsets.js
document.addEventListener('DOMContentLoaded', () => {
  const form       = document.getElementById('order-form');
  const grid       = document.getElementById('items-grid');
  const addBtn     = document.getElementById('add-item');
  const importBtn  = document.getElementById('btn-import-items');
  const templateEl = document.getElementById('empty-form-template');
  const totalForms = document.querySelector('input[name$="-TOTAL_FORMS"]');
  const tmplHtml   = templateEl.outerHTML;

  // 1) Handler para o botão "Importar Itens"
  if (importBtn) {
    importBtn.addEventListener('click', () => {
      window.location.href = importBtn.dataset.url;
    });
  }

  // 2) Impede o Enter disparar submit apenas dentro do grid (captura)
  if (grid) {
    const preventEnter = e => {
      if (e.key === 'Enter') e.preventDefault();
    };
    grid.addEventListener('keydown',  preventEnter, true);
    grid.addEventListener('keypress', preventEnter, true);
  }

  // 3) Remoção delegada de linhas
  grid.addEventListener('click', e => {
    if (e.target.matches('.remove-row')) {
      e.target.closest('.item-row').remove();
      updateIndices();
    }
  });

  // 4) Adição de linha
  addBtn.addEventListener('click', () => {
    const formIdx  = parseInt(totalForms.value, 10);
    let newRowHtml = tmplHtml
      .replace(/__prefix__/g, formIdx)
      .replace(/ id="empty-form-template"/, '');
    grid.insertAdjacentHTML('beforeend', newRowHtml);
    updateIndices();
  });

  // 5) Reindexação de names/ids e TOTAL_FORMS
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
