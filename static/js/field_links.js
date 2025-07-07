export function setupEditLinks(fieldNames, basePath, slugMap = {}) {
  fieldNames.forEach((field) => {
    const fieldId = 'id_' + field;
    const editLinkId = 'edit-' + field + '-link';

    const select = document.getElementById(fieldId);
    const editLink = document.getElementById(editLinkId);

    const urlSlug = slugMap[field] || field;

    function updateEditLink() {
      const selectedId = select.value;
      console.log(`🟡 [${field}] Selected value:`, selectedId);

      if (editLink) {
        if (selectedId) {
          editLink.href = `${basePath}/${urlSlug}/${selectedId}/edit/`;
          editLink.style.display = 'inline';
          console.log(`✅ Edit link updated to: ${editLink.href}`);
        } else {
          editLink.href = '#';
          editLink.style.display = 'none';
          console.log('🔕 Edit icon hidden (no value)');
        }
      } else {
        console.warn(`⚠️ Edit link with ID "${editLinkId}" not found for field "${field}"`);
      }
    }

    if (select && editLink) {
      console.log(`📌 Attaching listener to "${field}"`);
      select.addEventListener('change', updateEditLink);
      updateEditLink();
    } else {
      console.warn(`❌ Missing select or edit link for field: ${field}`);
    }
  });
}


export function setupFormsetEditLinks(fieldName, basePath, slugMap = {}) {
  const urlSlug = slugMap[fieldName] || fieldName;

  function updateEditLink(select) {
    const selectedId = select.value;

    let editLink = null;
    let el = select;
    const className = `.edit-${fieldName.replaceAll('_', '-')}-link`;
    for (let i = 0; i < 4; i++) {
      if (!el) break;
      editLink = el.parentElement?.querySelector(className);
      if (editLink) break;
      el = el.parentElement;
    }

    console.log(`🟡 [${fieldName}] Selected value:`, selectedId);
    console.log('🔍 Select element:', select);
    console.log('🔍 Edit link found?', !!editLink, editLink);

    if (editLink) {
      if (selectedId) {
        editLink.href = `${basePath}/${urlSlug}/${selectedId}/edit/`;
        editLink.style.display = 'inline';
        console.log(`✅ Edit link updated to: ${editLink.href}`);
      } else {
        editLink.href = '#';
        editLink.style.display = 'none';
        console.log(`🔕 Edit icon hidden (no value selected)`);
      }
    } else {
      console.warn(`⚠️ Edit link not found near:`, select);
    }
  }

  function handleNewSelect(select) {
    if (!select.dataset.editLinkAttached) {
      console.log(`📌 Attaching listener to select: ${select.name}`);
      select.addEventListener('change', () => updateEditLink(select));
      updateEditLink(select);
      select.dataset.editLinkAttached = 'true';
    } else {
      console.log(`🔁 Listener already attached to select: ${select.name}`);
    }
  }

  document.querySelectorAll(`select[name*="${fieldName}"]`).forEach(handleNewSelect);

  const grid = document.getElementById('model-application-grid');
  if (grid) {
    const observer = new MutationObserver(mutations => {
      for (const mutation of mutations) {
        for (const node of mutation.addedNodes) {
          if (node.nodeType === 1) {
            const select = node.querySelector(`select[name*="${fieldName}"]`);
            if (select) {
              console.log('➕ New select added to DOM:', select);
              handleNewSelect(select);
            }
          }
        }
      }
    });
    observer.observe(grid, { childList: true });
    console.log('👀 Watching for new rows in the grid:', grid);
  }
}

