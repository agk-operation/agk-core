document.addEventListener('DOMContentLoaded', () => {
  const addBtn          = document.getElementById('add-batch-item');
  const tableBody       = document.getElementById('batch-items-grid');
  const templateEl      = document.getElementById('empty-form-row');          // <template>
  const totalFormsInput = document.querySelector('input[name$="-TOTAL_FORMS"]');

  // checagem rápida
  if (!addBtn || !tableBody || !templateEl || !totalFormsInput) {
    console.error('Batch Formset: elemento não encontrado', {
      addBtn, tableBody, templateEl, totalFormsInput
    });
    return;
  }

  // 1) adicionar nova linha
  addBtn.addEventListener('click', () => {
    console.log('Batch Formset: Add clicked, TOTAL_FORMS was', totalFormsInput.value);
    const formCount = parseInt(totalFormsInput.value, 10);
    // clona o conteúdo do <template>
    const clone = templateEl.content.cloneNode(true);
    const tr = clone.querySelector('tr');
    // substitui o __prefix__ pelo índice correto
    tr.innerHTML = tr.innerHTML.replace(/__prefix__/g, formCount);
    tableBody.appendChild(tr);
    totalFormsInput.value = formCount + 1;
  });

  // 2) remover linha
  tableBody.addEventListener('click', e => {
    if (!e.target.classList.contains('remove-row')) return;
    const row = e.target.closest('tr');
    const delCheckbox = row.querySelector('input[type="checkbox"][name$="-DELETE"]');
    if (delCheckbox) {
      delCheckbox.checked = true;
      row.style.display = 'none';
    } else {
      row.remove();
      totalFormsInput.value = parseInt(totalFormsInput.value, 10) - 1;
    }
  });
});
