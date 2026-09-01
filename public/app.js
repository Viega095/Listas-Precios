// Aplicación Cliente - Comparador de Listas de Precios
class PriceComparatorApp {
  constructor() {
    this.currentStep = 1;
    this.uploadedFiles = {}; // 0, 1, 2
    this.mappings = {};
    this.configs = [
      { nombre: "Proveedor 1", iva_incluido: true, iva_percent: 21.0, descuento_percent: 0.0, recargo_percent: 0.0, bonificacion_percent: 0.0, modo_precio: "unitario", unidades_por_bulto: 1.0 },
      { nombre: "Proveedor 2", iva_incluido: true, iva_percent: 21.0, descuento_percent: 0.0, recargo_percent: 0.0, bonificacion_percent: 0.0, modo_precio: "unitario", unidades_por_bulto: 1.0 },
      { nombre: "Proveedor 3", iva_incluido: true, iva_percent: 21.0, descuento_percent: 0.0, recargo_percent: 0.0, bonificacion_percent: 0.0, modo_precio: "unitario", unidades_por_bulto: 1.0 }
    ];
    this.activeMappingTab = 0;
    this.comparisonResult = null;
    
    // Paginación y Filtrado
    this.currentPage = 1;
    this.pageSize = 100;
    this.filteredRows = [];
    this.currentViewMode = 'brands';
    this.activeTableFilter = 'todos';
    
    this.init();
  }

  init() {
    this.bindEvents();
    this.renderConfigCards();
    lucide.createIcons();
  }

  bindEvents() {
    // Drag and drop para las 3 tarjetas
    [0, 1, 2].forEach(idx => {
      const card = document.getElementById(`file-card-${idx}`);
      if (!card) return;
      card.addEventListener('dragover', (e) => {
        e.preventDefault();
        card.classList.add('border-sky-500', 'bg-sky-50/50');
      });
      card.addEventListener('dragleave', () => {
        card.classList.remove('border-sky-500', 'bg-sky-50/50');
      });
      card.addEventListener('drop', (e) => {
        e.preventDefault();
        card.classList.remove('border-sky-500', 'bg-sky-50/50');
        if (e.dataTransfer.files.length > 0) {
          this.handleFileSelect(idx, e.dataTransfer.files[0]);
        }
      });
      // Sincronizar nombre de proveedor
      const provInput = document.getElementById(`prov-name-${idx}`);
      if (provInput) {
        provInput.addEventListener('input', (e) => {
          this.configs[idx].nombre = e.target.value || `Proveedor ${idx + 1}`;
        });
      }
    });

    // Filtros de búsqueda
    const filterSearch = document.getElementById('filter-search');
    const tableSearch = document.getElementById('table-search');
    const filterStatus = document.getElementById('filter-status');
    const filterDiffRange = document.getElementById('filter-diff-range');
    const filterProvider = document.getElementById('filter-provider');
    const filterSort = document.getElementById('filter-sort');
    const selectPageSize = document.getElementById('select-page-size');

    if (filterSearch) filterSearch.addEventListener('input', () => this.applyFiltersAndRender());
    if (tableSearch) tableSearch.addEventListener('input', () => this.applyFiltersAndRender());
    if (filterStatus) filterStatus.addEventListener('change', () => this.applyFiltersAndRender());
    if (filterDiffRange) filterDiffRange.addEventListener('change', () => this.applyFiltersAndRender());
    if (filterProvider) filterProvider.addEventListener('change', () => this.applyFiltersAndRender());
    if (filterSort) filterSort.addEventListener('change', () => this.applyFiltersAndRender());
    
    if (selectPageSize) {
      selectPageSize.addEventListener('change', (e) => {
        this.pageSize = e.target.value === 'all' ? 999999 : parseInt(e.target.value);
        this.currentPage = 1;
        this.renderTablePage();
      });
    }

    document.getElementById('btn-prev-page')?.addEventListener('click', () => {
      if (this.currentPage > 1) {
        this.currentPage--;
        this.renderTablePage();
      }
    });

    document.getElementById('btn-next-page')?.addEventListener('click', () => {
      const maxPages = Math.ceil(this.filteredRows.length / this.pageSize) || 1;
      if (this.currentPage < maxPages) {
        this.currentPage++;
        this.renderTablePage();
      }
    });

    // Carga de sesión
    document.getElementById('input-load-session')?.addEventListener('change', (e) => {
      if (e.target.files.length > 0) {
        this.loadSessionFile(e.target.files[0]);
      }
    });

    // Guardado de sesión
    document.getElementById('btn-save-session')?.addEventListener('click', () => {
      window.location.href = '/api/session/save';
    });

    // Reinicio
    document.getElementById('btn-reset')?.addEventListener('click', () => {
      if (confirm('¿Deseás reiniciar la aplicación y comenzar una nueva comparación?')) {
        window.location.reload();
      }
    });
  }

  showLoading(title, desc) {
    document.getElementById('loading-title').innerText = title;
    document.getElementById('loading-desc').innerText = desc;
    document.getElementById('loading-overlay').classList.remove('hidden');
  }

  hideLoading() {
    document.getElementById('loading-overlay').classList.add('hidden');
  }

  showAlert(type, message) {
    const container = document.getElementById('global-alert-container');
    const colorClasses = type === 'error' ? 'bg-rose-50 border-rose-200 text-rose-800' : 'bg-emerald-50 border-emerald-200 text-emerald-800';
    const alertDiv = document.createElement('div');
    alertDiv.className = `p-3 rounded-lg border text-xs flex items-center justify-between shadow-sm ${colorClasses}`;
    alertDiv.innerHTML = `
      <div class="flex items-center gap-2">
        <i data-lucide="${type === 'error' ? 'alert-circle' : 'check-circle-2'}" class="w-4 h-4 shrink-0"></i>
        <span>${message}</span>
      </div>
      <button onclick="this.parentElement.remove()" class="text-slate-400 hover:text-slate-600 font-bold ml-4">✕</button>
    `;
    container.appendChild(alertDiv);
    lucide.createIcons();
    setTimeout(() => alertDiv.remove(), 8000);
  }

  goToStep(step) {
    this.currentStep = step;
    const sec1 = document.getElementById('section-step-1');
    const sec5 = document.getElementById('section-step-5');
    const nav1 = document.getElementById('nav-step-1');
    const nav5 = document.getElementById('nav-step-5');
    const btnBack = document.getElementById('btn-back-to-upload');

    if (step === 1) {
      if (sec1) sec1.classList.remove('hidden');
      if (sec5) sec5.classList.add('hidden');
      if (nav1) nav1.className = "step-btn active flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-sky-700 bg-sky-50 font-bold border border-sky-200 transition";
      if (nav5) nav5.className = "step-btn flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-slate-600 hover:bg-slate-100 transition";
      if (btnBack) btnBack.classList.add('hidden');
    } else {
      if (sec1) sec1.classList.add('hidden');
      if (sec5) sec5.classList.remove('hidden');
      if (nav1) nav1.className = "step-btn flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-slate-600 hover:bg-slate-100 transition";
      if (nav5) nav5.className = "step-btn active flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-sky-700 bg-sky-50 font-bold border border-sky-200 transition";
      if (btnBack) btnBack.classList.remove('hidden');
      this.renderResultsDashboard();
      this.renderDoubtfulList();
    }

    lucide.createIcons();
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  async handleFileSelect(listIdx, file) {
    if (!file) return;
    this.showLoading(`Cargando ${file.name}...`, "Detectando estructura y leyendo filas");
    
    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await fetch(`/api/upload/${listIdx}`, {
        method: 'POST',
        body: formData
      });
      const data = await res.json();
      
      if (!res.ok) throw new Error(data.detail || 'Error al subir archivo');

      this.uploadedFiles[listIdx] = data;
      this.mappings[listIdx] = data.detected_mapping;

      // Actualizar tarjeta visual
      document.getElementById(`file-info-${listIdx}`).classList.remove('hidden');
      document.getElementById(`file-name-${listIdx}`).innerText = data.filename;
      document.getElementById(`file-rows-${listIdx}`).innerText = `${data.total_rows.toLocaleString()} filas leídas`;
      document.getElementById(`file-card-${listIdx}`).classList.add('has-file');

      // Validar si al menos 2 listas están cargadas
      const uploadedCount = Object.keys(this.uploadedFiles).length;
      document.getElementById('btn-goto-step-2').disabled = uploadedCount < 2;

      this.showAlert('success', `Lista "${data.filename}" cargada correctamente con ${data.total_rows.toLocaleString()} productos.`);

    } catch (err) {
      this.showAlert('error', err.message);
    } finally {
      this.hideLoading();
      lucide.createIcons();
    }
  }

  toggleThirdList() {
    const card2 = document.getElementById('file-card-2');
    const placeholder = document.getElementById('card-placeholder-3');
    if (!card2) return;
    if (card2.classList.contains('hidden')) {
      card2.classList.remove('hidden');
      if (placeholder) placeholder.classList.add('hidden');
    } else {
      if (this.uploadedFiles[2]) {
        this.removeFile(2);
      }
      card2.classList.add('hidden');
      if (placeholder) placeholder.classList.remove('hidden');
    }
    lucide.createIcons();
  }

  async loadDemoData() {
    this.showLoading("Cargando catálogos de prueba...", "Cargando productos con precios y códigos de ejemplo");
    try {
      const res = await fetch('/api/load_demo');
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Error al cargar datos de prueba');

      document.getElementById('file-card-2')?.classList.remove('hidden');
      document.getElementById('card-placeholder-3')?.classList.add('hidden');

      data.files.forEach(f => {
        const idx = f.list_idx;
        this.uploadedFiles[idx] = f;
        this.mappings[idx] = f.detected_mapping;
        this.configs[idx].nombre = f.prov_name;

        document.getElementById(`file-info-${idx}`).classList.remove('hidden');
        document.getElementById(`file-name-${idx}`).innerText = f.filename;
        document.getElementById(`file-rows-${idx}`).innerText = `${f.total_rows.toLocaleString()} filas leídas`;
        document.getElementById(`file-card-${idx}`).classList.add('has-file');
        
        const provInput = document.getElementById(`prov-name-${idx}`);
        if (provInput) provInput.value = f.prov_name;
      });

      document.getElementById('btn-goto-step-2').disabled = false;
      this.showAlert('success', '¡Listas de prueba cargadas con éxito! Ya podés comparar los precios.');
    } catch (err) {
      this.showAlert('error', err.message);
    } finally {
      this.hideLoading();
      lucide.createIcons();
    }
  }

  async removeFile(listIdx) {
    try {
      await fetch(`/api/upload/${listIdx}`, { method: 'DELETE' });
      delete this.uploadedFiles[listIdx];
      delete this.mappings[listIdx];

      document.getElementById(`file-info-${listIdx}`).classList.add('hidden');
      document.getElementById(`file-card-${listIdx}`).classList.remove('has-file');
      document.getElementById(`file-input-${listIdx}`).value = '';

      const uploadedCount = Object.keys(this.uploadedFiles).length;
      document.getElementById('btn-goto-step-2').disabled = uploadedCount < 2;
    } catch (err) {
      console.error(err);
    }
  }

  // ========================================================
  // PASO 2: MAPEO DE COLUMNAS
  // ========================================================
  renderMappingView() {
    const tabsContainer = document.getElementById('mapping-list-tabs');
    const mappingContainer = document.getElementById('mapping-container');
    tabsContainer.innerHTML = '';
    
    const activeIndices = Object.keys(this.uploadedFiles).map(Number);
    if (activeIndices.length === 0) return;

    if (!activeIndices.includes(this.activeMappingTab)) {
      this.activeMappingTab = activeIndices[0];
    }

    activeIndices.forEach(idx => {
      const info = this.uploadedFiles[idx];
      const provName = this.configs[idx].nombre;
      const isActive = idx === this.activeMappingTab;
      
      const tabBtn = document.createElement('button');
      tabBtn.className = `px-3.5 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition ${
        isActive ? 'bg-sky-600 text-white shadow-sm' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
      }`;
      tabBtn.innerHTML = `<span>${provName}</span> <span class="text-[10px] opacity-75">(${info.total_rows.toLocaleString()} filas)</span>`;
      tabBtn.onclick = () => {
        this.activeMappingTab = idx;
        this.renderMappingView();
      };
      tabsContainer.appendChild(tabBtn);
    });

    const currentFile = this.uploadedFiles[this.activeMappingTab];
    if (!currentFile) return;

    const currentMapping = this.mappings[this.activeMappingTab] || {};
    const availableCols = currentFile.columns;

    const standardFields = [
      { key: "descripcion", label: "Descripción / Producto (*)", required: true, desc: "Nombre o descripción del artículo" },
      { key: "precio", label: "Precio / Costo (*)", required: true, desc: "Precio unitario o de lista" },
      { key: "codigo", label: "Código de Producto", required: false, desc: "Código interno del artículo" },
      { key: "codigo_barras", label: "Código de Barras / EAN / SKU", required: false, desc: "EAN13, GTIN o SKU para matching prioritario" },
      { key: "marca", label: "Marca / Fabricante", required: false, desc: "Marca del producto" },
      { key: "presentacion", label: "Presentación / Envase", required: false, desc: "Ej: 2.25L, 1kg, Pack x6" },
      { key: "unidad", label: "Unidad de Medida", required: false, desc: "Litros, Kilos, Unidades" },
      { key: "cantidad", label: "Cantidad / Stock", required: false, desc: "Cantidad disponible o por empaque" },
      { key: "precio_final", label: "Precio Final / Venta", required: false, desc: "Precio con IVA incluido si viene separado" },
      { key: "iva", label: "% Alícuota IVA", required: false, desc: "Columna de IVA del artículo" },
      { key: "descuento", label: "% Descuento", required: false, desc: "Descuento del artículo si aplica" }
    ];

    const hasDesc = !!currentMapping.descripcion;
    const hasPrice = !!(currentMapping.precio || currentMapping.precio_final);
    const isValidMapping = hasDesc && hasPrice;

    let bannerHtml = `
      <div class="p-3.5 rounded-xl text-xs flex items-center justify-between border ${
        isValidMapping ? 'bg-emerald-50 border-emerald-200 text-emerald-900 font-medium' : 'bg-amber-50 border-amber-200 text-amber-900 font-semibold'
      }">
        <div class="flex items-center gap-2">
          <i data-lucide="${isValidMapping ? 'check-circle-2' : 'alert-triangle'}" class="w-4 h-4 shrink-0 ${isValidMapping ? 'text-emerald-600' : 'text-amber-600'}"></i>
          <span>${
            isValidMapping 
              ? `✅ <b>Todo listo:</b> Las columnas esenciales (<b>Producto</b> y <b>Precio</b>) están asignadas correctamente para <b>${this.configs[this.activeMappingTab]?.nombre}</b>.`
              : `⚠️ <b>Atención:</b> Falta asignar la columna de <b>Producto</b> o <b>Precio</b> en este archivo para poder comparar.`
          }</span>
        </div>
        <span class="text-[11px] opacity-75">${currentFile.columns.length} columnas en el archivo</span>
      </div>
    `;

    let fieldsHtml = `
      ${bannerHtml}
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 bg-slate-50 p-4 rounded-xl border border-slate-200 mt-3">
    `;

    standardFields.forEach(f => {
      const selectedCol = currentMapping[f.key] || "";
      fieldsHtml += `
        <div class="space-y-1">
          <label class="block text-xs font-bold text-slate-700">
            ${f.label} ${f.required ? '<span class="text-rose-500">*</span>' : ''}
          </label>
          <select class="w-full text-xs border border-slate-300 rounded-lg p-2 bg-white focus:border-sky-500 outline-none"
                  onchange="window.app.updateColumnMapping(${this.activeMappingTab}, '${f.key}', this.value)">
            <option value="">-- No mapear / No presente --</option>
            ${availableCols.map(c => `
              <option value="${c}" ${c === selectedCol ? 'selected' : ''}>${c}</option>
            `).join('')}
          </select>
          <p class="text-[11px] text-slate-400">${f.desc}</p>
        </div>
      `;
    });

    fieldsHtml += `</div>`;

    const previewRows = currentFile.preview_rows || [];
    let previewHtml = `
      <div class="mt-6">
        <h4 class="text-xs font-bold text-slate-700 mb-2 flex items-center gap-1.5">
          <i data-lucide="table" class="w-4 h-4 text-sky-600"></i>
          Vista previa del archivo original (${currentFile.filename})
        </h4>
        <div class="overflow-x-auto border border-slate-200 rounded-lg max-h-48">
          <table class="w-full text-[11px] text-left">
            <thead class="bg-slate-100 text-slate-700 sticky top-0">
              <tr>${availableCols.map(c => `<th class="p-2 border-b border-slate-200">${c}</th>`).join('')}</tr>
            </thead>
            <tbody class="divide-y divide-slate-100">
              ${previewRows.slice(0, 5).map(r => `
                <tr class="hover:bg-slate-50">${availableCols.map(c => `<td class="p-2 truncate max-w-[160px]">${r[c] || ''}</td>`).join('')}</tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      </div>
    `;

    mappingContainer.innerHTML = fieldsHtml + previewHtml;
    lucide.createIcons();
  }

  updateColumnMapping(listIdx, stdKey, selectedCol) {
    if (!this.mappings[listIdx]) this.mappings[listIdx] = {};
    this.mappings[listIdx][stdKey] = selectedCol || null;
  }

  // ========================================================
  // PASO 3: CONFIGURACIÓN FINANCIERA
  // ========================================================
  renderConfigCards() {
    const container = document.getElementById('configs-container');
    if (!container) return;
    container.innerHTML = '';

    [0, 1, 2].forEach(idx => {
      const cfg = this.configs[idx];
      const isUploaded = !!this.uploadedFiles[idx];
      
      const card = document.createElement('div');
      card.className = `p-5 rounded-xl border ${isUploaded ? 'bg-white border-slate-300 shadow-sm' : 'bg-slate-50 border-slate-200 opacity-60'}`;
      card.innerHTML = `
        <div class="flex items-center justify-between mb-3">
          <h3 class="font-bold text-slate-800 text-sm flex items-center gap-2">
            <span class="w-2.5 h-2.5 rounded-full ${isUploaded ? 'bg-emerald-500' : 'bg-slate-300'}"></span>
            ${cfg.nombre}
          </h3>
          <span class="text-[11px] font-semibold px-2 py-0.5 rounded bg-slate-100 text-slate-600">Lista ${idx + 1}</span>
        </div>

        <div class="space-y-3 text-xs">
          <div>
            <label class="block font-semibold text-slate-700 mb-1">Tratamiento de IVA</label>
            <div class="flex items-center gap-3">
              <label class="flex items-center gap-1.5 cursor-pointer">
                <input type="radio" name="iva_inc_${idx}" value="true" ${cfg.iva_incluido ? 'checked' : ''} onchange="window.app.configs[${idx}].iva_incluido = true">
                <span>IVA Incluido</span>
              </label>
              <label class="flex items-center gap-1.5 cursor-pointer">
                <input type="radio" name="iva_inc_${idx}" value="false" ${!cfg.iva_incluido ? 'checked' : ''} onchange="window.app.configs[${idx}].iva_incluido = false">
                <span>+ IVA</span>
              </label>
            </div>
          </div>

          <div class="grid grid-cols-2 gap-2">
            <div>
              <label class="block font-semibold text-slate-700 mb-1">% IVA por defecto</label>
              <input type="number" step="0.5" value="${cfg.iva_percent}" class="w-full border border-slate-300 rounded p-1.5" onchange="window.app.configs[${idx}].iva_percent = parseFloat(this.value) || 0">
            </div>
            <div>
              <label class="block font-semibold text-slate-700 mb-1">% Descuento gral.</label>
              <input type="number" step="0.5" value="${cfg.descuento_percent}" class="w-full border border-slate-300 rounded p-1.5" onchange="window.app.configs[${idx}].descuento_percent = parseFloat(this.value) || 0">
            </div>
          </div>

          <div class="grid grid-cols-2 gap-2">
            <div>
              <label class="block font-semibold text-slate-700 mb-1">% Recargo</label>
              <input type="number" step="0.5" value="${cfg.recargo_percent}" class="w-full border border-slate-300 rounded p-1.5" onchange="window.app.configs[${idx}].recargo_percent = parseFloat(this.value) || 0">
            </div>
            <div>
              <label class="block font-semibold text-slate-700 mb-1">% Bonificación</label>
              <input type="number" step="0.5" value="${cfg.bonificacion_percent}" class="w-full border border-slate-300 rounded p-1.5" onchange="window.app.configs[${idx}].bonificacion_percent = parseFloat(this.value) || 0">
            </div>
          </div>

          <div class="border-t border-slate-100 pt-2">
            <label class="block font-semibold text-slate-700 mb-1">Modo de Precio</label>
            <div class="grid grid-cols-2 gap-2">
              <select class="border border-slate-300 rounded p-1.5 bg-white" onchange="window.app.configs[${idx}].modo_precio = this.value">
                <option value="unitario" ${cfg.modo_precio === 'unitario' ? 'selected' : ''}>Precio Unitario</option>
                <option value="bulto" ${cfg.modo_precio === 'bulto' ? 'selected' : ''}>Precio por Bulto/Caja</option>
              </select>
              <input type="number" min="1" step="1" placeholder="Unidades x bulto" value="${cfg.unidades_por_bulto}" class="border border-slate-300 rounded p-1.5" onchange="window.app.configs[${idx}].unidades_por_bulto = parseFloat(this.value) || 1">
            </div>
          </div>
        </div>
      `;
      container.appendChild(card);
    });
  }

  // ========================================================
  // PASO 4 & 5: PROCESAMIENTO Y RESULTADOS
  // ========================================================
  async processComparison() {
    this.showLoading("Procesando 100% de productos...", "Normalizando descripciones, emparejando catálogos y calculando ahorros óptimos");
    
    try {
      const filesData = {};
      Object.keys(this.uploadedFiles).forEach(k => {
        filesData[k] = this.uploadedFiles[k].raw_records || [];
      });

      const res = await fetch('/api/process', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          files_data: filesData,
          mappings: this.mappings,
          configs: this.configs,
          similarity_threshold: 85.0
        })
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Error en el procesamiento');

      this.comparisonResult = data;
      this.filteredRows = [...data.rows];

      // Actualizar badge de dudosos
      const doubtfulCount = data.stats.dudosos || 0;
      const badgeDudosos = document.getElementById('badge-dudosos');
      if (doubtfulCount > 0) {
        badgeDudosos.innerText = doubtfulCount;
        badgeDudosos.classList.remove('hidden');
      } else {
        badgeDudosos.classList.add('hidden');
      }

      document.getElementById('btn-save-session').classList.remove('hidden');

      this.goToStep(5);

      this.showAlert('success', `¡Procesamiento completo! Se analizaron ${data.total_items.toLocaleString()} artículos.`);

    } catch (err) {
      this.showAlert('error', err.message);
    } finally {
      this.hideLoading();
    }
  }

  renderDoubtfulList() {
    const container = document.getElementById('doubtful-list-container');
    const banner = document.getElementById('doubtful-banner');
    const drawer = document.getElementById('doubtful-drawer');
    const countText = document.getElementById('doubtful-count-text');
    if (!container) return;
    container.innerHTML = '';

    const doubtfulRows = (this.comparisonResult?.rows || []).filter(r => r.es_dudoso);

    if (doubtfulRows.length === 0) {
      if (banner) banner.classList.add('hidden');
      if (drawer) drawer.classList.add('hidden');
      return;
    }
    if (banner) banner.classList.remove('hidden');
    if (drawer) drawer.classList.remove('hidden');
    if (countText) countText.innerText = doubtfulRows.length;

    doubtfulRows.forEach(r => {
      const card = document.createElement('div');
      card.className = "bg-white border-2 border-amber-200/90 hover:border-amber-400 rounded-xl p-4 flex flex-col md:flex-row items-start md:items-center justify-between gap-4 transition shadow-xs";
      card.innerHTML = `
        <div class="space-y-2 text-xs flex-1">
          <div class="flex items-center gap-2">
            <span class="font-extrabold text-slate-900 text-sm">${r.producto}</span>
            <span class="bg-amber-100 text-amber-900 border border-amber-300 font-bold px-2 py-0.5 rounded text-[10px]">Similitud: ${Math.round(r.similitud || r.confidence || 0)}%</span>
          </div>
          <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5 pt-1">
            <div class="bg-slate-50 p-2 rounded-lg border border-slate-200">
              <span class="text-[10px] font-bold text-slate-500 uppercase block">${this.configs[0].nombre}</span>
              <span class="font-semibold text-slate-800">${r.desc_l1 || '<i class="text-slate-400">No presente</i>'}</span>
              <span class="block text-slate-500 font-medium text-[11px] mt-0.5">${r.precio_l1 ? '$' + r.precio_l1.toLocaleString('es-AR', {minimumFractionDigits: 2}) : '-'}</span>
            </div>
            <div class="bg-slate-50 p-2 rounded-lg border border-slate-200">
              <span class="text-[10px] font-bold text-slate-500 uppercase block">${this.configs[1].nombre}</span>
              <span class="font-semibold text-slate-800">${r.desc_l2 || '<i class="text-slate-400">No presente</i>'}</span>
              <span class="block text-slate-500 font-medium text-[11px] mt-0.5">${r.precio_l2 ? '$' + r.precio_l2.toLocaleString('es-AR', {minimumFractionDigits: 2}) : '-'}</span>
            </div>
            ${this.configs[2]?.nombre ? `
            <div class="bg-slate-50 p-2 rounded-lg border border-slate-200">
              <span class="text-[10px] font-bold text-slate-500 uppercase block">${this.configs[2].nombre}</span>
              <span class="font-semibold text-slate-800">${r.desc_l3 || '<i class="text-slate-400">No presente</i>'}</span>
              <span class="block text-slate-500 font-medium text-[11px] mt-0.5">${r.precio_l3 ? '$' + r.precio_l3.toLocaleString('es-AR', {minimumFractionDigits: 2}) : '-'}</span>
            </div>` : ''}
          </div>
        </div>
        <div class="flex items-center gap-2 shrink-0 self-end md:self-center">
          <button onclick="window.app.overrideMatch('${r.group_id}', 'confirm')" class="bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold px-3.5 py-2 rounded-xl flex items-center gap-1.5 shadow-xs transition">
            <i data-lucide="check" class="w-4 h-4"></i> Confirmar
          </button>
          <button onclick="window.app.overrideMatch('${r.group_id}', 'unlink')" class="bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-bold px-3.5 py-2 rounded-xl flex items-center gap-1.5 border border-slate-300 transition">
            <i data-lucide="split" class="w-4 h-4"></i> Separar
          </button>
        </div>
      `;
      container.appendChild(card);
    });
    lucide.createIcons();
  }

  async overrideMatch(groupId, action) {
    try {
      const res = await fetch('/api/match/override', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ group_id: groupId, action: action })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail);

      this.comparisonResult.rows = data.rows;
      this.comparisonResult.totals = data.totals;
      this.filteredRows = [...data.rows];

      const badgeDudosos = document.getElementById('badge-dudosos');
      const dCount = data.stats?.dudosos || 0;
      if (dCount > 0) {
        badgeDudosos.innerText = dCount;
        badgeDudosos.classList.remove('hidden');
      } else {
        badgeDudosos.classList.add('hidden');
      }

      this.renderDoubtfulList();
      this.renderResultsDashboard();
      this.applyFiltersAndRender();
      this.showAlert('success', action === 'confirm' ? 'Coincidencia confirmada.' : 'Productos separados correctamente.');
    } catch (err) {
      this.showAlert('error', err.message);
    }
  }

  async overrideAll(action) {
    try {
      const res = await fetch('/api/match/override', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ group_id: 'ALL', action: action })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail);

      this.comparisonResult.rows = data.rows;
      this.comparisonResult.totals = data.totals;
      this.filteredRows = [...data.rows];

      document.getElementById('badge-dudosos').classList.add('hidden');
      this.renderDoubtfulList();
      this.renderResultsDashboard();
      this.applyFiltersAndRender();
      this.showAlert('success', action === 'confirm_all' ? 'Se confirmaron todos los productos dudosos.' : 'Se separaron todos los productos dudosos.');
    } catch (err) {
      this.showAlert('error', err.message);
    }
  }

  renderResultsDashboard() {
    if (!this.comparisonResult) return;
    const totals = this.comparisonResult.totals;
    const numFiles = Object.keys(this.uploadedFiles).length;

    const totL1 = totals.totales_generales?.[0] || 0;
    const totL2 = totals.totales_generales?.[1] || 0;

    // Tarjeta 1: Total Lista 1
    const elTitleL1 = document.getElementById('kpi-title-l1');
    if (elTitleL1) elTitleL1.innerText = `Total ${this.configs[0]?.nombre || 'Lista 1'}`;
    const elTotL1 = document.getElementById('kpi-total-l1');
    if (elTotL1) elTotL1.innerText = `$${totL1.toLocaleString('es-AR', { minimumFractionDigits: 2 })}`;

    // Tarjeta 2: Total Lista 2
    const elTitleL2 = document.getElementById('kpi-title-l2');
    if (elTitleL2) elTitleL2.innerText = `Total ${this.configs[1]?.nombre || 'Lista 2'}`;
    const elTotL2 = document.getElementById('kpi-total-l2');
    if (elTotL2) elTotL2.innerText = `$${totL2.toLocaleString('es-AR', { minimumFractionDigits: 2 })}`;

    // Tarjeta 3: Variación General (Aumento o Rebaja)
    const elVarMonto = document.getElementById('kpi-variacion-monto');
    const elVarPct = document.getElementById('kpi-variacion-pct');
    const elIconVar = document.getElementById('kpi-icon-variacion');
    const elCardVar = document.getElementById('kpi-card-variacion');

    const diffMonto = totals.variacion_monto_l2_vs_l1 ?? (totL2 - totL1);
    const diffPct = totals.variacion_pct_l2_vs_l1 ?? (totL1 > 0 ? ((totL2 - totL1) / totL1) * 100 : 0);

    if (elVarMonto && elVarPct) {
      if (diffMonto > 0.01) {
        elVarMonto.className = "text-2xl font-black text-rose-700 mt-2";
        elVarMonto.innerText = `+$${diffMonto.toLocaleString('es-AR', { minimumFractionDigits: 2 })}`;
        elVarPct.className = "text-xs font-bold text-rose-700 mt-1";
        elVarPct.innerText = `🔺 +${diffPct.toFixed(2)}% de aumento general`;
      } else if (diffMonto < -0.01) {
        elVarMonto.className = "text-2xl font-black text-emerald-700 mt-2";
        elVarMonto.innerText = `-$${Math.abs(diffMonto).toLocaleString('es-AR', { minimumFractionDigits: 2 })}`;
        elVarPct.className = "text-xs font-bold text-emerald-700 mt-1";
        elVarPct.innerText = `🔻 -${Math.abs(diffPct).toFixed(2)}% de disminución general`;
      } else {
        elVarMonto.className = "text-2xl font-black text-slate-800 mt-2";
        elVarMonto.innerText = `$0.00`;
        elVarPct.className = "text-xs font-bold text-slate-600 mt-1";
        elVarPct.innerText = `🟢 0.00% sin variación global`;
      }
    }

    // Tarjeta 4: Movimiento de Precios
    const elCountAumentos = document.getElementById('kpi-count-aumentos');
    if (elCountAumentos) elCountAumentos.innerText = (totals.count_aumentos || 0).toLocaleString();
    const elCountRebajas = document.getElementById('kpi-count-rebajas');
    if (elCountRebajas) elCountRebajas.innerText = (totals.count_rebajas || 0).toLocaleString();
    const elCountIguales = document.getElementById('kpi-count-iguales');
    if (elCountIguales) elCountIguales.innerText = (totals.count_iguales || 0).toLocaleString();

    // Tabla de resumen de proveedores
    const diffTotalEl = document.getElementById('txt-diferencia-total-listas');
    if (diffTotalEl) {
      diffTotalEl.innerText = `Diferencia entre listas: $${Math.abs(diffMonto).toLocaleString('es-AR', { minimumFractionDigits: 2 })}`;
    }
    
    const tbodyProv = document.getElementById('tbody-summary-providers');
    if (tbodyProv) {
      tbodyProv.innerHTML = '';

      [0, 1, 2].forEach(idx => {
        if (this.uploadedFiles[idx]) {
          const totG = totals.totales_generales[idx] || 0;
          const cntB = totals.conteo_mas_baratos[idx] || 0;
          const cntE = totals.conteo_exclusivos[idx] || 0;

          let diffVsL1Str = '-';
          let pctVsL1Str = '<span class="text-slate-400 font-normal">Base de referencia</span>';

          if (idx > 0 && totL1 > 0) {
            const d = totG - totL1;
            const p = (d / totL1) * 100;
            if (d > 0.01) {
              diffVsL1Str = `<span class="text-rose-700 font-bold">+$${d.toLocaleString('es-AR', { minimumFractionDigits: 2 })}</span>`;
              pctVsL1Str = `<span class="text-rose-700 font-bold">🔺 +${p.toFixed(2)}%</span>`;
            } else if (d < -0.01) {
              diffVsL1Str = `<span class="text-emerald-700 font-bold">-$${Math.abs(d).toLocaleString('es-AR', { minimumFractionDigits: 2 })}</span>`;
              pctVsL1Str = `<span class="text-emerald-700 font-bold">🔻 -${Math.abs(p).toFixed(2)}%</span>`;
            } else {
              diffVsL1Str = `<span class="text-slate-600 font-bold">$0.00</span>`;
              pctVsL1Str = `<span class="text-slate-600 font-bold">0.00%</span>`;
            }
          }

          tbodyProv.innerHTML += `
            <tr class="hover:bg-slate-50 transition-colors">
              <td class="py-3 px-4 font-bold text-slate-900">${this.configs[idx].nombre}</td>
              <td class="py-3 px-4 text-right font-extrabold text-slate-900">$${totG.toLocaleString('es-AR', { minimumFractionDigits: 2 })}</td>
              <td class="py-3 px-4 text-right font-medium">${diffVsL1Str}</td>
              <td class="py-3 px-4 text-right font-medium">${pctVsL1Str}</td>
              <td class="py-3 px-4 text-center font-bold text-emerald-800">${cntB}</td>
              <td class="py-3 px-4 text-center font-semibold text-slate-600">${cntE}</td>
            </tr>
          `;
        }
      });
    }

    this.renderBrandsView();
    lucide.createIcons();
  }

  // ========================================================
  // SELECTOR DE VISTA (POR MARCAS vs TABLA DETALLADA)
  // ========================================================
  switchView(mode) {
    this.currentViewMode = mode;
    const btnBrands = document.getElementById('btn-view-brands');
    const btnTable = document.getElementById('btn-view-table');
    const cBrands = document.getElementById('container-view-brands');
    const cTable = document.getElementById('container-view-table');

    if (mode === 'brands') {
      if (btnBrands) btnBrands.className = "px-3 py-1.5 rounded-md font-bold text-sky-800 bg-white shadow-xs transition flex items-center gap-1.5";
      if (btnTable) btnTable.className = "px-3 py-1.5 rounded-md font-medium text-slate-600 hover:text-slate-900 transition flex items-center gap-1.5";
      if (cBrands) cBrands.classList.remove('hidden');
      if (cTable) cTable.classList.add('hidden');
      this.applyFiltersAndRender();
    } else {
      if (btnBrands) btnBrands.className = "px-3 py-1.5 rounded-md font-medium text-slate-600 hover:text-slate-900 transition flex items-center gap-1.5";
      if (btnTable) btnTable.className = "px-3 py-1.5 rounded-md font-bold text-sky-800 bg-white shadow-xs transition flex items-center gap-1.5";
      if (cBrands) cBrands.classList.add('hidden');
      if (cTable) cTable.classList.remove('hidden');
      this.applyFiltersAndRender();
    }
    lucide.createIcons();
  }

  setTableFilter(filterKey) {
    this.activeTableFilter = filterKey;
    document.querySelectorAll('.tbl-filter-btn').forEach(btn => {
      btn.className = "tbl-filter-btn text-xs font-semibold px-3 py-1.5 rounded-lg bg-white border border-slate-300 text-slate-700 hover:bg-slate-50";
    });
    const activeBtn = event?.target?.closest('.tbl-filter-btn');
    if (activeBtn) {
      activeBtn.className = "tbl-filter-btn active text-xs font-semibold px-3 py-1.5 rounded-lg bg-slate-800 text-white shadow-xs";
    }
    this.applyFiltersAndRender();
  }

  // ========================================================
  // FILTRADO Y RENDERIZADO
  // ========================================================
  applyFiltersAndRender() {
    if (!this.comparisonResult) return;

    const searchTerm = (
      document.getElementById('table-search')?.value || 
      document.getElementById('filter-search')?.value || 
      ''
    ).toLowerCase().trim();
    
    const filterBtn = this.activeTableFilter || 'todos';

    let list = this.comparisonResult.rows.filter(r => {
      if (searchTerm) {
        const matchName = (r.producto || '').toLowerCase().includes(searchTerm);
        const matchCode = (r.codigo || '').toLowerCase().includes(searchTerm);
        const matchBrand = (r.marca || '').toLowerCase().includes(searchTerm);
        const matchPres = (r.presentacion || '').toLowerCase().includes(searchTerm);
        if (!matchName && !matchCode && !matchBrand && !matchPres) return false;
      }

      if (filterBtn === 'mas_barato_l1' && r.proveedor_mas_barato_idx !== 0) return false;
      if (filterBtn === 'mas_barato_l2' && r.proveedor_mas_barato_idx !== 1) return false;
      if (filterBtn === 'mas_barato_l3' && r.proveedor_mas_barato_idx !== 2) return false;
      if (filterBtn === 'exclusivos' && r.present_count !== 1) return false;
      if (filterBtn === 'dudosos' && !r.es_dudoso) return false;

      return true;
    });

    this.filteredRows = list;
    this.currentPage = 1;

    this.renderBrandsView();
  }

  renderBrandsView() {
    const container = document.getElementById('container-view-brands');
    if (!container || !this.comparisonResult) return;
    container.innerHTML = '';

    const rows = this.filteredRows || this.comparisonResult.rows || [];
    if (rows.length === 0) {
      container.innerHTML = `<div class="p-8 text-center text-slate-400 bg-white rounded-xl border border-slate-200">No se encontraron productos con el filtro actual.</div>`;
      return;
    }

    const brandMap = {};
    rows.forEach(r => {
      let bName = (r.marca || '').trim();
      if (!bName || bName.toLowerCase() === 'sin marca') {
        const words = (r.producto || '').split(' ');
        bName = words.length > 0 ? words[0] : 'General';
      }
      bName = bName.charAt(0).toUpperCase() + bName.slice(1);
      if (!brandMap[bName]) brandMap[bName] = [];
      brandMap[bName].push(r);
    });

    const sortedBrands = Object.keys(brandMap).sort((a, b) => brandMap[b].length - brandMap[a].length);

    sortedBrands.forEach(brand => {
      const items = brandMap[brand];
      const card = document.createElement('div');
      card.className = "bg-white rounded-xl border border-slate-300 shadow-sm overflow-hidden";
      
      let itemsHtml = '';
      items.forEach((it, itemIdx) => {
        // Gris más visible y contrastado pero agradable
        const bgClass = (itemIdx % 2 === 0) ? 'bg-white' : 'bg-slate-100/90';

        let diffBadge = '';
        const uploadedCount = Object.keys(this.uploadedFiles).length;
        
        if (uploadedCount === 2 && it.precio_l1 !== null && it.precio_l2 !== null) {
          const diff = it.precio_l2 - it.precio_l1;
          const pct = it.precio_l1 > 0 ? (diff / it.precio_l1) * 100 : 0;
          if (diff > 0.01) {
            diffBadge = `<span class="bg-rose-100 text-rose-900 font-extrabold px-3 py-1.5 rounded-lg text-xs border border-rose-300 flex items-center justify-center gap-1 shadow-2xs">🔺 Subió +$${diff.toLocaleString('es-AR', {minimumFractionDigits: 2})} (+${pct.toFixed(1)}%)</span>`;
          } else if (diff < -0.01) {
            diffBadge = `<span class="bg-emerald-100 text-emerald-900 font-extrabold px-3 py-1.5 rounded-lg text-xs border border-emerald-300 flex items-center justify-center gap-1 shadow-2xs">🔻 Bajó -$${Math.abs(diff).toLocaleString('es-AR', {minimumFractionDigits: 2})} (${pct.toFixed(1)}%)</span>`;
          } else {
            diffBadge = `<span class="bg-slate-200 text-slate-800 font-bold px-3 py-1.5 rounded-lg text-xs border border-slate-300 flex items-center justify-center gap-1">🟢 Mismo precio</span>`;
          }
        } else if (it.diferencia_dinero > 0) {
          diffBadge = `<span class="bg-sky-100 text-sky-950 font-bold px-3 py-1.5 rounded-lg text-xs border border-sky-300 flex items-center justify-center gap-1">Diferencia: $${it.diferencia_dinero.toLocaleString('es-AR', {minimumFractionDigits: 2})} (${it.diferencia_porcentaje.toFixed(1)}%)</span>`;
        } else if (it.estado_precio === 'Precio igual') {
          diffBadge = `<span class="bg-slate-200 text-slate-800 font-bold px-3 py-1.5 rounded-lg text-xs border border-slate-300 flex items-center justify-center gap-1">🟢 Mismo precio</span>`;
        } else {
          diffBadge = `<span class="bg-emerald-100 text-emerald-900 font-bold px-3 py-1.5 rounded-lg text-xs border border-emerald-300 flex items-center justify-center gap-1">${it.proveedor_mas_barato}</span>`;
        }

        let provPricesHtml = '';
        [0, 1, 2].forEach(idx => {
          if (this.uploadedFiles[idx]) {
            const pVal = it[`precio_l${idx + 1}`];
            const pName = this.configs[idx].nombre;
            const isBest = (it.proveedor_mas_barato_idx === idx);
            provPricesHtml += `
              <div class="flex items-center gap-1.5 text-xs px-3 py-1 rounded-lg border ${
                isBest && it.present_count > 1 
                  ? 'bg-emerald-50 border-emerald-400 text-emerald-950 font-black ring-1 ring-emerald-500/40' 
                  : 'bg-white border-slate-300 text-slate-800 font-semibold'
              }">
                <span class="text-[10px] text-slate-500 font-bold uppercase tracking-wider">${pName}:</span>
                <span class="font-extrabold text-slate-900">${pVal ? '$' + pVal.toLocaleString('es-AR', { minimumFractionDigits: 2 }) : '<i class="text-slate-400 font-normal">No presente</i>'}</span>
                ${isBest && it.present_count > 1 ? '<span class="text-[9px] bg-emerald-700 text-white px-1.5 py-0.2 rounded font-black ml-0.5">LÍDER</span>' : ''}
              </div>
            `;
          }
        });

        itemsHtml += `
          <div class="px-4 py-3.5 ${bgClass} hover:bg-sky-50 transition-colors border-b border-slate-300 last:border-b-0 flex flex-col md:flex-row md:items-center justify-between gap-3">
            <div class="space-y-1.5 flex-1 max-w-2xl">
              <div class="font-black text-slate-950 text-sm tracking-tight">${it.producto}</div>
              
              <!-- Nombres exactos de cada lista comparada -->
              <div class="flex flex-col sm:flex-row flex-wrap gap-1.5 text-[11px] bg-slate-50/90 p-1.5 rounded-lg border border-slate-200">
                ${it.desc_l1 ? `<span class="inline-flex items-center gap-1"><span class="font-bold text-slate-700 text-[10px] uppercase bg-slate-200/80 px-1.5 py-0.5 rounded">${this.configs[0].nombre}:</span> <span class="text-slate-900 font-medium">${it.desc_l1}</span></span>` : ''}
                ${it.desc_l1 && it.desc_l2 ? `<span class="text-slate-300 hidden sm:inline">|</span>` : ''}
                ${it.desc_l2 ? `<span class="inline-flex items-center gap-1"><span class="font-bold text-slate-700 text-[10px] uppercase bg-slate-200/80 px-1.5 py-0.5 rounded">${this.configs[1].nombre}:</span> <span class="text-slate-900 font-medium">${it.desc_l2}</span></span>` : ''}
                ${it.desc_l3 ? `<span class="inline-flex items-center gap-1"><span class="font-bold text-slate-700 text-[10px] uppercase bg-slate-200/80 px-1.5 py-0.5 rounded">${this.configs[2]?.nombre}:</span> <span class="text-slate-900 font-medium">${it.desc_l3}</span></span>` : ''}
              </div>

              <div class="flex flex-wrap items-center gap-2 text-[11px]">
                ${it.codigo ? `<span class="bg-white border border-slate-300 text-slate-700 font-mono px-2 py-0.5 rounded shadow-2xs font-semibold">Cód: ${it.codigo}</span>` : ''}
                ${it.presentacion ? `<span class="bg-white border border-slate-300 text-slate-700 px-2 py-0.5 rounded shadow-2xs font-semibold">Pres: ${it.presentacion}</span>` : ''}
                ${it.es_dudoso ? `<span class="bg-amber-100 border border-amber-400 text-amber-950 font-bold px-2 py-0.5 rounded">⚠️ Similar</span>` : ''}
              </div>
            </div>
            <div class="flex flex-wrap items-center gap-3 md:gap-5 shrink-0">
              <div class="flex flex-wrap items-center gap-2">
                ${provPricesHtml}
              </div>
              <div class="min-w-[175px]">${diffBadge}</div>
            </div>
          </div>
        `;
      });

      card.innerHTML = `
        <div class="bg-slate-200/90 px-4 py-3 border-b border-slate-300 flex items-center justify-between">
          <div class="flex items-center gap-2">
            <span class="text-base">🏷️</span>
            <h4 class="font-black text-slate-950 text-sm tracking-tight">${brand}</h4>
            <span class="bg-slate-300 text-slate-900 text-[10px] font-black px-2.5 py-0.5 rounded-full border border-slate-400/80">${items.length} productos</span>
          </div>
        </div>
        <div>
          ${itemsHtml}
        </div>
      `;

      container.appendChild(card);
    });

    lucide.createIcons();
  }

  renderTablePage() {
    const tbody = document.getElementById('tbody-products') || document.getElementById('tbody-comparison-rows');
    if (!tbody) return;
    tbody.innerHTML = '';

    const total = this.filteredRows ? this.filteredRows.length : 0;
    const startIdx = (this.currentPage - 1) * this.pageSize;
    const endIdx = Math.min(startIdx + this.pageSize, total);
    const pageRows = (this.filteredRows || []).slice(startIdx, endIdx);
    const maxPages = Math.ceil(total / this.pageSize) || 1;

    const countInfo = document.getElementById('txt-pagination-info');
    if (countInfo) {
      countInfo.innerText = `Mostrando ${total > 0 ? startIdx + 1 : 0} a ${endIdx} de ${total.toLocaleString()} productos`;
    }
    const pageInfo = document.getElementById('txt-current-page');
    if (pageInfo) {
      pageInfo.innerText = `${this.currentPage} / ${maxPages}`;
    }
    const btnPrev = document.getElementById('btn-prev-page');
    const btnNext = document.getElementById('btn-next-page');
    if (btnPrev) btnPrev.disabled = this.currentPage <= 1;
    if (btnNext) btnNext.disabled = this.currentPage >= maxPages;

    pageRows.forEach((r, i) => {
      const globalRowIdx = startIdx + i;
      const rowNum = globalRowIdx + 1;
      const isEven = (i % 2 === 0);
      const rowClass = isEven ? 'bg-white' : 'bg-slate-100/90';

      const minP = r.precio_min;
      const p1Str = r.precio_l1 !== null ? `$${r.precio_l1.toLocaleString('es-AR', { minimumFractionDigits: 2 })}` : '<span class="text-slate-400 italic">No disponible</span>';
      const p2Str = r.precio_l2 !== null ? `$${r.precio_l2.toLocaleString('es-AR', { minimumFractionDigits: 2 })}` : '<span class="text-slate-400 italic">No disponible</span>';
      const p3Str = r.precio_l3 !== null ? `$${r.precio_l3.toLocaleString('es-AR', { minimumFractionDigits: 2 })}` : '<span class="text-slate-400 italic">No disponible</span>';

      const isP1Best = (r.precio_l1 !== null && minP !== null && Math.abs(r.precio_l1 - minP) < 0.001 && (r.precio_l2 !== null || r.precio_l3 !== null));
      const isP2Best = (r.precio_l2 !== null && minP !== null && Math.abs(r.precio_l2 - minP) < 0.001 && (r.precio_l1 !== null || r.precio_l3 !== null));
      const isP3Best = (r.precio_l3 !== null && minP !== null && Math.abs(r.precio_l3 - minP) < 0.001 && (r.precio_l1 !== null || r.precio_l2 !== null));

      let pctBadgeClass = 'bg-slate-100 text-slate-700 border border-slate-300';
      if (r.diferencia_porcentaje > 35) {
        pctBadgeClass = 'bg-rose-100 text-rose-900 font-black border border-rose-300';
      } else if (r.diferencia_porcentaje > 15) {
        pctBadgeClass = 'bg-amber-100 text-amber-900 font-bold border border-amber-300';
      } else if (r.diferencia_porcentaje > 0) {
        pctBadgeClass = 'bg-emerald-100 text-emerald-900 font-bold border border-emerald-300';
      }

      const tr = document.createElement('tr');
      tr.className = `${rowClass} hover:bg-sky-50 border-b border-slate-300 transition-colors cursor-pointer`;
      tr.title = "Hacé clic para ver el desglose completo del producto";
      tr.onclick = () => this.openProductModal(globalRowIdx);

      tr.innerHTML = `
        <td class="py-3 px-3 text-center font-mono text-[11px] font-bold text-slate-500 border-r border-slate-200">
          ${rowNum}
        </td>
        <td class="py-3 px-3 border-r border-slate-200">
          <div class="font-bold text-slate-900 text-xs">${r.producto}</div>
          <div class="text-[10px] text-slate-500 flex flex-col gap-0.5 mt-1">
            ${r.desc_l1 ? `<span><b>${this.configs[0].nombre}:</b> ${r.desc_l1}</span>` : ''}
            ${r.desc_l2 ? `<span><b>${this.configs[1].nombre}:</b> ${r.desc_l2}</span>` : ''}
          </div>
        </td>
        <td class="py-3 px-2 text-slate-600 font-mono text-[11px]">${r.codigo || '-'}</td>
        <td class="py-3 px-2 text-slate-700 font-medium">${r.marca || '-'}</td>
        <td class="py-3 px-2 text-slate-600">${r.presentacion || '-'}</td>
        
        <td class="py-3 px-3 text-right font-medium ${isP1Best ? 'bg-emerald-100 text-emerald-950 font-black' : 'text-slate-800'}">
          ${isP1Best ? '<span class="text-emerald-700 font-black mr-1">✓</span>' : ''}${p1Str}
        </td>
        <td class="py-3 px-3 text-right font-medium ${isP2Best ? 'bg-emerald-100 text-emerald-950 font-black' : 'text-slate-800'}">
          ${isP2Best ? '<span class="text-emerald-700 font-black mr-1">✓</span>' : ''}${p2Str}
        </td>
        <td class="py-3 px-3 text-right font-medium ${isP3Best ? 'bg-emerald-100 text-emerald-950 font-black' : 'text-slate-800'}">
          ${isP3Best ? '<span class="text-emerald-700 font-black mr-1">✓</span>' : ''}${p3Str}
        </td>

        <td class="py-3 px-3 text-center font-bold text-emerald-950 bg-emerald-50 border-x border-slate-200 truncate max-w-[140px]">${r.proveedor_mas_barato}</td>
        <td class="py-3 px-3 text-right font-bold text-slate-900">$${r.diferencia_dinero.toLocaleString('es-AR', { minimumFractionDigits: 2 })}</td>
        <td class="py-3 px-3 text-right">
          <span class="px-2 py-0.5 rounded text-[11px] ${pctBadgeClass}" title="${r.explicacion_porcentaje}">
            ${r.diferencia_porcentaje.toFixed(2)}%
          </span>
        </td>
        <td class="py-3 px-2 text-center">
          <button class="text-sky-600 hover:text-sky-800 p-1 rounded hover:bg-sky-100" title="Ver detalle"><i data-lucide="eye" class="w-4 h-4"></i></button>
        </td>
      `;
      tbody.appendChild(tr);
    });

    lucide.createIcons();
  }

  prevPage() {
    if (this.currentPage > 1) {
      this.currentPage--;
      this.renderTablePage();
    }
  }

  nextPage() {
    const total = this.filteredRows ? this.filteredRows.length : 0;
    const maxPages = Math.ceil(total / this.pageSize) || 1;
    if (this.currentPage < maxPages) {
      this.currentPage++;
      this.renderTablePage();
    }
  }

  // ========================================================
  // MODAL DETALLE DE PRODUCTO
  // ========================================================
  openProductModal(rowIndex) {
    const r = this.filteredRows[rowIndex];
    if (!r) return;

    document.getElementById('modal-status-badge').innerText = r.estado_precio;
    document.getElementById('modal-product-title').innerText = r.producto;
    document.getElementById('modal-product-meta').innerText = `Código: ${r.codigo || 'Sin código'} | Marca: ${r.marca || 'N/A'} | Presentación: ${r.presentacion || 'N/A'}`;

    const provContainer = document.getElementById('modal-providers-breakdown');
    provContainer.innerHTML = '';

    const listKeys = [
      { key: 'l1', idx: 0, p: r.precio_l1, p_orig: r.precio_l1_orig, code: r.cod_l1, desc: r.desc_l1 },
      { key: 'l2', idx: 1, p: r.precio_l2, p_orig: r.precio_l2_orig, code: r.cod_l2, desc: r.desc_l2 },
      { key: 'l3', idx: 2, p: r.precio_l3, p_orig: r.precio_l3_orig, code: r.cod_l3, desc: r.desc_l3 }
    ];

    listKeys.forEach(item => {
      const cfg = this.configs[item.idx];
      const isBest = (item.p !== null && r.precio_min !== null && Math.abs(item.p - r.precio_min) < 0.001);
      
      const card = document.createElement('div');
      card.className = `p-3.5 rounded-xl border ${isBest ? 'bg-emerald-50/80 border-emerald-300 ring-1 ring-emerald-400' : 'bg-slate-50 border-slate-200'}`;
      card.innerHTML = `
        <div class="flex items-center justify-between font-bold text-slate-800 mb-2">
          <span>${cfg.nombre}</span>
          ${isBest ? '<span class="bg-emerald-600 text-white text-[10px] px-1.5 py-0.5 rounded font-bold">Más Barato</span>' : ''}
        </div>
        <div class="space-y-1 text-[11px] text-slate-600">
          <div><b>Precio Efectivo:</b> <span class="font-bold ${isBest ? 'text-emerald-800 text-sm' : 'text-slate-800'}">${item.p !== null ? '$' + item.p.toLocaleString('es-AR', {minimumFractionDigits: 2}) : 'No disponible'}</span></div>
          <div><b>Precio Original:</b> ${item.p_orig !== null ? '$' + item.p_orig.toLocaleString('es-AR', {minimumFractionDigits: 2}) : '-'}</div>
          <div><b>Código:</b> ${item.code || '-'}</div>
          <div class="truncate" title="${item.desc}"><b>Desc:</b> ${item.desc || '-'}</div>
        </div>
      `;
      provContainer.appendChild(card);
    });

    const diffContainer = document.getElementById('modal-diff-breakdown');
    diffContainer.innerHTML = `
      <div class="flex items-center justify-between">
        <span class="font-semibold text-slate-700">Diferencia monetaria (Ahorro directo):</span>
        <span class="font-black text-slate-900 text-sm">$${r.diferencia_dinero.toLocaleString('es-AR', { minimumFractionDigits: 2 })}</span>
      </div>
      <div class="flex items-center justify-between">
        <span class="font-semibold text-slate-700">Diferencia porcentual:</span>
        <span class="font-black text-rose-700 text-sm">${r.diferencia_porcentaje.toFixed(2)}%</span>
      </div>
      <p class="text-[11px] text-slate-500 pt-1 border-t border-slate-200 mt-1">${r.explicacion_porcentaje}</p>
    `;

    document.getElementById('product-detail-modal').classList.remove('hidden');
    lucide.createIcons();
  }

  // ========================================================
  // EXPORTACIONES Y SESIÓN
  // ========================================================
  async exportFile(format) {
    if (!this.comparisonResult) {
      this.showAlert('error', 'No hay resultados para exportar.');
      return;
    }
    this.showLoading("Generando archivo...", `Exportando resultados a ${format.toUpperCase()}`);
    try {
      const res = await fetch(`/api/export/${format}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          comparison_results: this.comparisonResult,
          configs: this.configs
        })
      });
      if (!res.ok) throw new Error('Error al generar exportación');
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `Comparacion_Precios.${format === 'excel' ? 'xlsx' : (format === 'csv' ? 'csv' : 'pdf')}`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (e) {
      this.showAlert('error', e.message);
    } finally {
      this.hideLoading();
    }
  }

  async exportOrder(listIdx) {
    if (!this.comparisonResult) {
      this.showAlert('error', 'No hay resultados para exportar.');
      return;
    }
    const provName = this.configs[listIdx].nombre.replace(/\s+/g, '_');
    this.showLoading("Generando Pedido...", `Generando Excel para ${this.configs[listIdx].nombre}`);
    try {
      const res = await fetch(`/api/export/order/${listIdx}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          comparison_results: this.comparisonResult,
          configs: this.configs
        })
      });
      if (!res.ok) throw new Error('Error al generar pedido de compra');
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `Pedido_${provName}.xlsx`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (e) {
      this.showAlert('error', e.message);
    } finally {
      this.hideLoading();
    }
  }

  async loadSessionFile(file) {
    const formData = new FormData();
    formData.append('file', file);

    this.showLoading("Cargando sesión...", "Restaurando datos y comparaciones anteriores");
    try {
      const res = await fetch('/api/session/load', {
        method: 'POST',
        body: formData
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail);

      this.configs = data.configs;
      this.comparisonResult = { totals: data.totals, rows: data.rows };
      this.filteredRows = [...data.rows];

      this.goToStep(5);
      this.showAlert('success', 'Sesión cargada exitosamente.');
    } catch (err) {
      this.showAlert('error', err.message);
    } finally {
      this.hideLoading();
    }
  }
}

// Iniciar aplicación al cargar el DOM
window.addEventListener('DOMContentLoaded', () => {
  window.app = new PriceComparatorApp();
});
