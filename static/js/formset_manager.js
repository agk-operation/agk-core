export function setupInlineFormset({
  gridId,
  addButtonId,
  emptyFormId,
  totalFormsId,
  rowClass = 'formset-row',
  removeButtonClass = 'remove-row'
}) {
  console.log('[Formset] Initializing...');

  document.addEventListener('DOMContentLoaded', () => {
    const grid = document.getElementById(gridId);
    const addButton = document.getElementById(addButtonId);
    const emptyFormTemplate = document.getElementById(emptyFormId);
    const totalFormsInput = document.getElementById(totalFormsId);

    let hasError = false;

    if (!grid) {
      console.error(`❌ Elemento com id="${gridId}" não encontrado (gridId)`);
      hasError = true;
    }
    if (!addButton) {
      console.error(`❌ Elemento com id="${addButtonId}" não encontrado (addButtonId)`);
      hasError = true;
    }
    if (!emptyFormTemplate) {
      console.error(`❌ Elemento com id="${emptyFormId}" não encontrado (emptyFormTemplate)`);
      hasError = true;
    }
    if (!totalFormsInput) {
      console.error(`❌ Elemento com id="${totalFormsId}" não encontrado (totalFormsInput)`);
      hasError = true;
    }

    if (hasError) {
      console.warn('⚠️ Formset não inicializado: pelo menos um elemento está ausente.');
      return;
    }

    console.log('[Formset] Done.');

    function updateFormIndices() {
      const rows = grid.querySelectorAll(`.${rowClass}`);
      rows.forEach((row, index) => {
        row.querySelectorAll('input, select, textarea, label').forEach(el => {
          if (el.name) el.name = el.name.replace(/-(\d+)-/, `-${index}-`);
          if (el.id) el.id = el.id.replace(/-(\d+)-/, `-${index}-`);
          if (el.htmlFor) el.htmlFor = el.htmlFor.replace(/-(\d+)-/, `-${index}-`);
        });
      });
      totalFormsInput.value = rows.length;
    }

    addButton.addEventListener('click', () => {
      const formIndex = parseInt(totalFormsInput.value, 10);

      const isTemplate = emptyFormTemplate.tagName.toLowerCase() === 'template';
      const templateContent = isTemplate
        ? emptyFormTemplate.content.cloneNode(true).firstElementChild
        : emptyFormTemplate.cloneNode(true);

      if (!templateContent) {
        console.error('❌ Template está vazio ou inválido.');
        return;
      }

      let html = templateContent.outerHTML
        .replace(/__prefix__/g, formIndex)
        .replace(`id="${emptyFormId}"`, '');

      grid.insertAdjacentHTML('beforeend', html);
      updateFormIndices();
    });

    grid.addEventListener('click', (e) => {
      if (e.target.classList.contains(removeButtonClass)) {
        const row = e.target.closest(`.${rowClass}`);
        if (row) {
          row.remove();
          updateFormIndices();
        }
      }
    });
  });
}
