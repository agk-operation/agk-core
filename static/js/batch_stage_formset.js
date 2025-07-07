// static/js/batch_stage_formset.js
document.addEventListener('DOMContentLoaded', () => {
  const grid             = document.getElementById('stages-grid');
  const removedContainer = document.getElementById('removed-stages');
  if (!grid || !removedContainer) return;

  // Cria o badge e associa row diretamente a ele
  function addBadge(row) {
    const idx  = row.dataset.idx;
    const name = row.cells[0].textContent.trim();
    // se já existir badge para este idx, não duplica
    if (removedContainer.querySelector(`.badge[data-idx="${idx}"]`)) return;

    const badge = document.createElement('span');
    badge.className = 'badge bg-secondary me-1';
    badge.dataset.idx = idx;
    badge._row = row;            // guardo a linha aqui!
    badge.textContent = name;

    // botão de “reativar” com ícone "+"
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'btn btn-sm btn-success btn-undo-stage ms-2';
    btn.setAttribute('aria-label', 'Reativar');
    btn.innerHTML = '<i class="bi bi-plus"></i>';
    badge.appendChild(btn);

    removedContainer.appendChild(badge);
  }

  // Inicial: move ao bucket as que já vierem desmarcadas
  grid.querySelectorAll('tr.stage-row').forEach(row => {
    const hidden = row.querySelector(`input[name="stages-${row.dataset.idx}-active"]`);
    if (hidden && !hidden.value) {
      row.style.display = 'none';
      addBadge(row);
    }
  });

  // Cliques no ícone de lixeira
  grid.addEventListener('click', e => {
    const btn = e.target.closest('.remove-row-stage');
    if (!btn) return;
    const row = btn.closest('tr.stage-row');
    const hidden = row.querySelector(`input[name="stages-${row.dataset.idx}-active"]`);

    // escondo a linha e limpo o hidden
    row.style.display = 'none';
    if (hidden) hidden.value = '';

    // crio o badge
    addBadge(row);
  });

  // Cliques no botão "+" do badge (reativar)
  removedContainer.addEventListener('click', e => {
    const btn = e.target.closest('.btn-undo-stage');
    if (!btn) return;
    const badge = btn.closest('span.badge');
    const row   = badge._row;  // pego direto do badge

    // reapareço a linha e marco o hidden
    row.style.display = '';
    const hidden = row.querySelector(`input[name="stages-${badge.dataset.idx}-active"]`);
    if (hidden) hidden.value = 'on';

    // removo o badge
    badge.remove();
  });
});

document.addEventListener('DOMContentLoaded', () => {
  const grid = document.getElementById('stages-grid');
  if (!grid) return;

  // ... (seu código atual de addBadge, remove logic, etc) ...

  // --- Novo: força largura da coluna de nome ao maior conteúdo ---
  (function fixNameColWidth() {
    // seleciona todas as células de nome de etapa
    const cells = grid.querySelectorAll('td.stage-name-col');
    if (cells.length === 0) return;

    // mede scrollWidth (largura natural) de cada célula
    let maxW = 0;
    cells.forEach(c => {
      const w = c.scrollWidth;
      if (w > maxW) maxW = w;
    });
    // adiciona um pequeno padding extra (ajuste se quiser)
    const finalW = maxW + 16; // 16px de folga

    // aplica no <th> também
    const header = document.querySelector('th.stage-name-col');
    if (header) header.style.width = `${finalW}px`;

    // aplica em todas as <td>
    cells.forEach(c => {
      c.style.width = `${finalW}px`;
      c.style.minWidth = `${finalW}px`;
      c.style.maxWidth = `${finalW}px`;
    });
  })();

});