document.addEventListener('DOMContentLoaded', function() {
  // Onde estão as linhas do formset
  const itemsGrid      = document.getElementById('items-grid');
  // A linha oculta que usamos como template
  const emptyRow       = document.getElementById('empty-form-template');
  // O input de TOTAL_FORMS do management_form
  const totalFormsInput = document.querySelector('input[name$="-TOTAL_FORMS"]');
  // Automaticamente descobre o prefixo (ex: "items")
  const prefix         = totalFormsInput.name.replace('-TOTAL_FORMS', '');

  // Ao clicar em “Add Item”
  document.getElementById('add-item').addEventListener('click', function() {
    const formCount = parseInt(totalFormsInput.value, 10);
    // Clona a linha-OCULTA
    const newRow = emptyRow.cloneNode(true);

    // Remove o id e a classe de oculto
    newRow.removeAttribute('id');
    newRow.classList.remove('d-none');

    // Substitui todos os __prefix__ pelo índice atual
    newRow.innerHTML = newRow.innerHTML.replace(/__prefix__/g, formCount);

    // Anexa no final da tabela
    itemsGrid.appendChild(newRow);

    // Atualiza o TOTAL_FORMS
    totalFormsInput.value = formCount + 1;
  });

  // Delegate para o botão “Remover” nas linhas novas
  itemsGrid.addEventListener('click', function(e) {
    if (e.target.matches('.remove-row')) {
      const row = e.target.closest('tr');
      row.remove();
      // Reconta apenas as linhas visíveis, sem o template
      const visible = itemsGrid.querySelectorAll('tr.item-row:not(.d-none)');
      totalFormsInput.value = visible.length;
    }
  });
});
