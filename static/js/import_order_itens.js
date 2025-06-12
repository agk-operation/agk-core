document.getElementById('import-form')
  .addEventListener('submit', function(e) {
    // 1) Pega o form principal pelos seus nomes de campo
    const orderForm = document.getElementById('order-form');
    const customer  = orderForm.querySelector('select[name="customer"], input[name="customer"]');
    const exporter  = orderForm.querySelector('select[name="exporter"], input[name="exporter"]');
    const company   = orderForm.querySelector('select[name="company"], input[name="company"]');

    // 2) Copia o valor para os hidden inputs
    document.getElementById('import-customer').value   = customer?.value || '';
    document.getElementById('import-exporter').value   = exporter?.value || '';
    document.getElementById('import-company').value   = company?.value || '';
    // (o form GET vai agora incluir esses parâmetros na URL)
});