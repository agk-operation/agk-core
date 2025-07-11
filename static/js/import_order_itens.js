document.addEventListener('DOMContentLoaded', () => {
  const importForm = document.getElementById('import-form');
  if (!importForm) return;

  importForm.addEventListener('submit', function(e) {
    // 1) Pega o form principal pelos seus nomes de campo
    const form = document.getElementById('order-form');
    const customer = form.querySelector('[name="customer"]')?.value || '';
    const exporter = form.querySelector('[name="exporter"]')?.value || '';
    const company  = form.querySelector('[name="company"]')?.value  || '';

    // 2) Copia o valor para os hidden inputs do form de import
    document.getElementById('import-customer').value = customer;
    document.getElementById('import-exporter').value = exporter;
    document.getElementById('import-company').value  = company;
    // agora o GET vai incluir esses hidden fields na URL
  });
});