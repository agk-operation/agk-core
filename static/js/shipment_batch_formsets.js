function activateSelect2() {
  $('select.select2').select2({
    width: '100%',
    placeholder: function() {
      return $(this).data('placeholder') || 'Selecione';
    },
    allowClear: true
  });
}

document.addEventListener('DOMContentLoaded', () => {
  activateSelect2();

  const grid = document.getElementById('batches-grid');
  const addBtn = document.getElementById('add-batch');
  const total = document.getElementById('id_sb-TOTAL_FORMS');
  const template = document.getElementById('batch-empty-template').innerHTML;

  addBtn?.addEventListener('click', () => {
    const count = parseInt(total.value, 10);
    const html = template.replace(/__prefix__/g, count);
    grid.insertAdjacentHTML('beforeend', html);
    total.value = count + 1;
    activateSelect2(); // Ativa nos novos campos
  });

  grid.addEventListener('click', e => {
    if (e.target.closest('.remove-row')) {
      e.preventDefault();
      e.target.closest('.batch-row').remove();
    }
  });
});