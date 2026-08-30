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
    const filterStatus = document.getElementById('filter-status');
    const filterDiffRange = document.getElementById('filter-diff-range');
    const filterProvider = document.getElementById('filter-provider');
    const filterSort = document.getElementById('filter-sort');
    const selectPageSize = document.getElementById('select-page-size');

    if (filterSearch) filterSearch.addEventListener('input', () => this.applyFiltersAndRender());
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
    document.querySelectorAll('.step-section').forEach(s => s.classList.add('hidden'));
    document.getElementById(`section-step-${step}`).classList.remove('hidden');

    // Actualizar botones del wizard
    for (let i = 1; i <= 5; i++) {
      const btn = document.getElementById(`nav-step-${i}`);
      if (i === step) {
        btn.className = "step-btn active flex items-center gap-2 px-3 py-1.5 rounded-lg text-sky-700 bg-sky-50 font-semibold border border-sky-200";
      } else if (i < step) {
        btn.className = "step-btn flex items-center gap-2 px-3 py-1.5 rounded-lg text-slate-700 hover:bg-slate-100";
      } else {
        btn.className = "step-btn flex items-center gap-2 px-3 py-1.5 rounded-lg text-slate-400 hover:bg-slate-50";
      }
    }

    if (step === 2) this.renderMappingView();
    if (step === 3) this.renderConfigCards();
    if (step === 4) this.renderDoubtfulList();
    if (step === 5) this.renderResultsDashboard();

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

      // Validar si al menos 1 lista está cargada
      const uploadedCount = Object.keys(this.uploadedFiles).length;
      document.getElementById('btn-goto-step-2').disabled = uploadedCount === 0;

      this.showAlert('success', `Lista "${data.filename}" cargada correctamente con ${data.total_rows.toLocaleString()} productos.`);

    } catch (err) {
      this.showAlert('error', err.message);
    } finally {
      this.hideLoading();
      lucide.createIcons();
    }
  }

  async loadDemoData() {
    this.showLoading("Cargando 3 catálogos de prueba...", "Cargando 10.000 productos con precios y códigos de ejemplo");
    try {
      const res = await fetch('/api/load_demo', { method: 'POST' });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Error al cargar datos de prueba');

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
      this.showAlert('success', '¡3 listas de prueba cargadas con éxito! Ya podés continuar al siguiente paso.');
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
      document.getElementById('btn-goto-step-2').disabled = uploadedCount === 0;
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
      const res = await fetch('/api/process', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
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

      if (doubtfulCount > 0) {
        this.goToStep(4);
      } else {
        this.goToStep(5);
      }

      this.showAlert('success', `¡Procesamiento completo! Se analizaron ${data.total_items.toLocaleString()} artículos.`);

    } catch (err) {
      this.showAlert('error', err.message);
    } finally {
      this.hideLoading();
    }
  }

  renderDoubtfulList() {
    const container = document.getElementById('doubtful-list-container');
    const noMsg = document.getElementById('no-doubtful-msg');
    container.innerHTML = '';

    const doubtfulRows = (this.comparisonResult?.rows || []).filter(r => r.es_dudoso);

    if (doubtfulRows.length === 0) {
      noMsg.classList.remove('hidden');
      return;
    }
    noMsg.classList.add('hidden');

    doubtfulRows.forEach(r => {
      const card = document.createElement('div');
      card.className = "bg-amber-50/70 border border-amber-200 rounded-xl p-4 flex flex-col md:flex-row items-start md:items-center justify-between gap-4";
      card.innerHTML = `
        <div class="space-y-1 text-xs">
          <div class="flex items-center gap-2">
            <span class="font-bold text-slate-800 text-sm">${r.producto}</span>
            <span class="bg-amber-100 text-amber-800 border border-amber-300/60 px-2 py-0.5 rounded text-[10px] font-semibold">Similitud: ${r.confidence}%</span>
          </div>
          <div class="text-slate-600 grid grid-cols-1 sm:grid-cols-3 gap-2 mt-2">
            <div><b>${this.configs[0].nombre}:</b> ${r.desc_l1 || '<i>No presente</i>'} (${r.precio_l1 ? '$' + r.precio_l1 : '-'})</div>
            <div><b>${this.configs[1].nombre}:</b> ${r.desc_l2 || '<i>No presente</i>'} (${r.precio_l2 ? '$' + r.precio_l2 : '-'})</div>
            <div><b>${this.configs[2].nombre}:</b> ${r.desc_l3 || '<i>No presente</i>'} (${r.precio_l3 ? '$' + r.precio_l3 : '-'})</div>
          </div>
        </div>
        <div class="flex items-center gap-2 shrink-0">
          <button onclick="window.app.overrideMatch('${r.group_id}', 'confirm')" class="bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold px-3 py-1.5 rounded-lg flex items-center gap-1 shadow-sm">
            <i data-lucide="check" class="w-3.5 h-3.5"></i> Confirmar
          </button>
          <button onclick="window.app.overrideMatch('${r.group_id}', 'unlink')" class="bg-slate-200 hover:bg-slate-300 text-slate-700 text-xs font-semibold px-3 py-1.5 rounded-lg flex items-center gap-1">
            <i data-lucide="split" class="w-3.5 h-3.5"></i> Separar
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
      this.showAlert('success', action === 'confirm_all' ? 'Se confirmaron todos los productos dudosos.' : 'Se separaron todos los productos dudosos.');
    } catch (err) {
      this.showAlert('error', err.message);
    }
  }

  renderResultsDashboard() {
    if (!this.comparisonResult) return;
    const totals = this.comparisonResult.totals;

    // KPI Cards
    document.getElementById('kpi-total-optimo').innerText = `$${totals.total_optimo_comparables.toLocaleString('es-AR', { minimumFractionDigits: 2 })}`;
    const subOpt = document.getElementById('kpi-total-optimo-sub');
    if (subOpt) {
      subOpt.innerText = `Catálogo total (con exclusivos): $${totals.total_compra_optima.toLocaleString('es-AR', { minimumFractionDigits: 2 })}`;
    }
    
    // Ahorro Máximo
    let maxAhorro = 0;
    let maxAhorroPct = 0;
    Object.values(totals.ahorros || {}).forEach(a => {
      if (a.ahorro_dinero > maxAhorro) {
        maxAhorro = a.ahorro_dinero;
        maxAhorroPct = a.ahorro_porcentaje;
      }
    });
    document.getElementById('kpi-max-ahorro').innerText = `$${maxAhorro.toLocaleString('es-AR', { minimumFractionDigits: 2 })}`;
    document.getElementById('kpi-max-ahorro-pct').innerText = `${maxAhorroPct.toFixed(2)}% de ahorro potencial máximo`;

    document.getElementById('kpi-total-items').innerText = totals.total_productos_comparados.toLocaleString();
    document.getElementById('kpi-items-detail').innerText = `${totals.total_productos_comparables.toLocaleString()} comparables | ${totals.total_productos_exclusivos.toLocaleString()} exclusivos`;

    // Generar Consejo Ejecutivo Directo (Explicación para humanos)
    const adviceBox = document.getElementById('text-executive-advice');
    if (adviceBox) {
      // Encontrar el proveedor con más artículos baratos
      let bestProvIdx = 0;
      let maxCheapestCount = -1;
      [0, 1, 2].forEach(idx => {
        if (this.uploadedFiles[idx]) {
          const count = totals.conteo_mas_baratos[idx] || 0;
          if (count > maxCheapestCount) {
            maxCheapestCount = count;
            bestProvIdx = idx;
          }
        }
      });

      const bestProvName = this.configs[bestProvIdx]?.nombre || `Proveedor ${bestProvIdx + 1}`;
      const totalComp = totals.total_productos_comparables || 1;
      const bestProvPct = ((maxCheapestCount / totalComp) * 100).toFixed(1);

      adviceBox.innerHTML = `
        <div class="flex items-start gap-2">
          <span class="font-bold text-slate-900">🏆 Opción Líder:</span>
          <span>Si querés comprarle a un solo proveedor para ahorrar tiempo, <b>${bestProvName}</b> es tu mejor opción (tiene el precio más bajo en el <b>${bestProvPct}%</b> de los artículos comparables).</span>
        </div>
        <div class="flex items-start gap-2">
          <span class="font-bold text-emerald-800">💰 Estrategia de Ahorro Máximo:</span>
          <span>Si dividís tu compra adquiriendo cada producto al proveedor más barato (Canasta Óptima), ahorrás hasta <b>$${maxAhorro.toLocaleString('es-AR', {minimumFractionDigits: 2})}</b> (${maxAhorroPct.toFixed(2)}%).</span>
        </div>
        <div class="flex items-start gap-2">
          <span class="font-bold text-sky-800">📋 Pedidos Listos:</span>
          <span>Hacé clic en el botón <b>"Descargar Pedido (.xlsx)"</b> al lado de cada proveedor para bajar la planilla lista con solo los productos que conviene comprarle a cada uno.</span>
        </div>
      `;
    }

    // Ganadores en KPI
    const leadersContainer = document.getElementById('kpi-cheapest-leaders');
    leadersContainer.innerHTML = '';
    [0, 1, 2].forEach(idx => {
      if (this.uploadedFiles[idx]) {
        const count = totals.conteo_mas_baratos[idx] || 0;
        leadersContainer.innerHTML += `<div><b>${this.configs[idx].nombre}:</b> ${count.toLocaleString()} más baratos</div>`;
      }
    });

    // Tabla de resumen de proveedores
    document.getElementById('txt-diferencia-total-listas').innerText = `Diferencia total monetaria entre listas: $${totals.diferencia_total_listas.toLocaleString('es-AR', { minimumFractionDigits: 2 })}`;
    
    const tbodyProv = document.getElementById('tbody-summary-providers');
    tbodyProv.innerHTML = '';

    [0, 1, 2].forEach(idx => {
      if (this.uploadedFiles[idx]) {
        const totC = totals.totales_comparables[idx] || 0;
        const totG = totals.totales_generales[idx] || 0;
        const ah = totals.ahorros[idx] || {};
        const cntB = totals.conteo_mas_baratos[idx] || 0;
        const cntE = totals.conteo_exclusivos[idx] || 0;

        tbodyProv.innerHTML += `
          <tr class="hover:bg-slate-50">
            <td class="py-2.5 px-3 font-semibold text-slate-800">${this.configs[idx].nombre}</td>
            <td class="py-2.5 px-3 text-right font-medium">$${totC.toLocaleString('es-AR', { minimumFractionDigits: 2 })}</td>
            <td class="py-2.5 px-3 text-right font-medium">$${totG.toLocaleString('es-AR', { minimumFractionDigits: 2 })}</td>
            <td class="py-2.5 px-3 text-right text-emerald-700 font-bold">$${(ah.ahorro_dinero || 0).toLocaleString('es-AR', { minimumFractionDigits: 2 })}</td>
            <td class="py-2.5 px-3 text-right text-emerald-700 font-bold">${(ah.ahorro_porcentaje || 0).toFixed(2)}%</td>
            <td class="py-2.5 px-3 text-center">${cntB}</td>
            <td class="py-2.5 px-3 text-center">${cntE}</td>
            <td class="py-2.5 px-3 text-center">
              <button onclick="window.app.exportOrder(${idx})" class="bg-sky-50 hover:bg-sky-100 text-sky-800 border border-sky-300 font-bold px-2 py-1 rounded text-[11px] flex items-center gap-1 mx-auto transition shadow-xs" title="Descargar planilla de Excel con solo los productos que conviene comprar a este proveedor">
                <i data-lucide="download" class="w-3.5 h-3.5"></i> Pedido .xlsx
              </button>
            </td>
          </tr>
        `;
      }
    });

    // Fila Canasta Óptima
    tbodyProv.innerHTML += `
      <tr class="bg-emerald-50 text-emerald-950 font-bold">
        <td class="py-2.5 px-3 flex items-center gap-1.5"><i data-lucide="sparkles" class="w-4 h-4 text-emerald-600"></i> CANASTA ÓPTIMA</td>
        <td class="py-2.5 px-3 text-right">$${totals.total_optimo_comparables.toLocaleString('es-AR', { minimumFractionDigits: 2 })}</td>
        <td class="py-2.5 px-3 text-right">$${totals.total_compra_optima.toLocaleString('es-AR', { minimumFractionDigits: 2 })}</td>
        <td class="py-2.5 px-3 text-right">-</td>
        <td class="py-2.5 px-3 text-right">-</td>
        <td class="py-2.5 px-3 text-center">Todos los ítems</td>
        <td class="py-2.5 px-3 text-center">-</td>
        <td class="py-2.5 px-3 text-center text-slate-400 font-normal text-[10px]">Combinada</td>
      </tr>
    `;

    // Encabezados de proveedores en la tabla principal
    document.getElementById('th-prov-0').innerText = `Precio ${this.configs[0].nombre}`;
    document.getElementById('th-prov-1').innerText = `Precio ${this.configs[1].nombre}`;
    document.getElementById('th-prov-2').innerText = `Precio ${this.configs[2].nombre}`;

    this.applyFiltersAndRender();
    lucide.createIcons();
  }

  // ========================================================
  // FILTRADO Y RENDERIZADO DE TABLA VIRTUAL/PAGINADA
  // ========================================================
  applyFiltersAndRender() {
    if (!this.comparisonResult) return;

    const searchTerm = (document.getElementById('filter-search')?.value || '').toLowerCase().trim();
    const statusFilter = document.getElementById('filter-status')?.value || 'all';
    const diffRange = document.getElementById('filter-diff-range')?.value || 'all';
    const providerFilter = document.getElementById('filter-provider')?.value || 'all';
    const sortOrder = document.getElementById('filter-sort')?.value || 'diff_pct_desc';

    let list = this.comparisonResult.rows.filter(r => {
      // Búsqueda de texto
      if (searchTerm) {
        const matchName = (r.producto || '').toLowerCase().includes(searchTerm);
        const matchCode = (r.codigo || '').toLowerCase().includes(searchTerm);
        const matchBrand = (r.marca || '').toLowerCase().includes(searchTerm);
        if (!matchName && !matchCode && !matchBrand) return false;
      }

      // Filtro de Estado
      if (statusFilter === 'en_3_listas' && r.present_count !== 3) return false;
      if (statusFilter === 'en_2_listas' && r.present_count !== 2) return false;
      if (statusFilter === 'exclusivo' && r.present_count !== 1) return false;
      if (statusFilter === 'precio_igual' && r.estado_precio !== 'Precio igual') return false;
      if (statusFilter === 'dudoso' && !r.es_dudoso) return false;

      // Filtro de Rango de Diferencia %
      if (diffRange === 'gt_50' && (r.diferencia_porcentaje || 0) < 50) return false;
      if (diffRange === 'gt_25' && (r.diferencia_porcentaje || 0) < 25) return false;
      if (diffRange === 'gt_10' && (r.diferencia_porcentaje || 0) < 10) return false;
      if (diffRange === 'equal' && (r.diferencia_porcentaje || 0) > 0.001) return false;

      // Filtro de Proveedor Más Barato
      if (providerFilter !== 'all') {
        const targetIdx = parseInt(providerFilter);
        if (r.proveedor_mas_barato_idx !== targetIdx) return false;
      }

      return true;
    });

    // Ordenamiento
    list.sort((a, b) => {
      if (sortOrder === 'diff_pct_desc') return (b.diferencia_porcentaje || 0) - (a.diferencia_porcentaje || 0);
      if (sortOrder === 'diff_money_desc') return (b.diferencia_dinero || 0) - (a.diferencia_dinero || 0);
      if (sortOrder === 'name_asc') return (a.producto || '').localeCompare(b.producto || '');
      if (sortOrder === 'price_min_asc') return (a.precio_min || 999999999) - (b.precio_min || 999999999);
      if (sortOrder === 'price_min_desc') return (b.precio_min || 0) - (a.precio_min || 0);
      return 0;
    });

    this.filteredRows = list;
    this.currentPage = 1;
    this.renderTablePage();
  }

  renderTablePage() {
    const tbody = document.getElementById('tbody-comparison-rows');
    if (!tbody) return;
    tbody.innerHTML = '';

    const total = this.filteredRows.length;
    const totalAll = this.comparisonResult?.rows?.length || 0;
    document.getElementById('txt-table-count').innerText = `Mostrando ${total.toLocaleString()} de ${totalAll.toLocaleString()} productos procesados`;

    const startIdx = (this.currentPage - 1) * this.pageSize;
    const endIdx = Math.min(startIdx + this.pageSize, total);
    const pageRows = this.filteredRows.slice(startIdx, endIdx);

    const maxPages = Math.ceil(total / this.pageSize) || 1;
    document.getElementById('txt-pagination-info').innerText = `Página ${this.currentPage} de ${maxPages}`;
    document.getElementById('btn-prev-page').disabled = this.currentPage <= 1;
    document.getElementById('btn-next-page').disabled = this.currentPage >= maxPages;

    pageRows.forEach((r, i) => {
      const globalRowIdx = startIdx + i;
      const rowNum = globalRowIdx + 1;
      const minP = r.precio_min;
      
      const isEven = (i % 2 === 0);
      const rowClass = isEven ? 'row-even' : 'row-odd';

      const p1Str = r.precio_l1 !== null ? `$${r.precio_l1.toLocaleString('es-AR', { minimumFractionDigits: 2 })}` : '<span class="text-slate-400 italic">No disponible</span>';
      const p2Str = r.precio_l2 !== null ? `$${r.precio_l2.toLocaleString('es-AR', { minimumFractionDigits: 2 })}` : '<span class="text-slate-400 italic">No disponible</span>';
      const p3Str = r.precio_l3 !== null ? `$${r.precio_l3.toLocaleString('es-AR', { minimumFractionDigits: 2 })}` : '<span class="text-slate-400 italic">No disponible</span>';

      const isP1Best = (r.precio_l1 !== null && minP !== null && Math.abs(r.precio_l1 - minP) < 0.001 && (r.precio_l2 !== null || r.precio_l3 !== null));
      const isP2Best = (r.precio_l2 !== null && minP !== null && Math.abs(r.precio_l2 - minP) < 0.001 && (r.precio_l1 !== null || r.precio_l3 !== null));
      const isP3Best = (r.precio_l3 !== null && minP !== null && Math.abs(r.precio_l3 - minP) < 0.001 && (r.precio_l1 !== null || r.precio_l2 !== null));

      // Badge de porcentaje con tonalidad de alerta
      let pctBadgeClass = 'bg-slate-100 text-slate-600';
      if (r.diferencia_porcentaje > 35) {
        pctBadgeClass = 'bg-rose-100 text-rose-800 font-bold border border-rose-200';
      } else if (r.diferencia_porcentaje > 15) {
        pctBadgeClass = 'bg-amber-100 text-amber-800 font-semibold border border-amber-200';
      } else if (r.diferencia_porcentaje > 0) {
        pctBadgeClass = 'bg-emerald-50 text-emerald-800 font-semibold border border-emerald-200';
      }

      const tr = document.createElement('tr');
      tr.className = `row-comparison ${rowClass}`;
      tr.title = "Hacé clic para ver el desglose completo del producto";
      tr.onclick = () => this.openProductModal(globalRowIdx);

      tr.innerHTML = `
        <td class="py-3 px-3 text-center sticky-col-1 border-r border-slate-200 font-mono text-[11px] font-semibold text-slate-500">
          ${rowNum}
        </td>
        <td class="py-3 px-3 sticky-col-2 border-r border-slate-200 font-bold text-slate-900 truncate max-w-[260px]">
          ${r.producto}
        </td>
        <td class="py-3 px-3 text-slate-600 font-mono text-[11px]">${r.codigo || '-'}</td>
        <td class="py-3 px-3 text-slate-700 font-medium">${r.marca || '-'}</td>
        <td class="py-3 px-3 text-slate-600">${r.presentacion || '-'}</td>
        <td class="py-3 px-3 text-center font-semibold text-slate-700">${r.cantidad}</td>
        
        <!-- Precios -->
        <td class="py-3 px-3 text-right font-medium ${isP1Best ? 'bg-emerald-100 text-emerald-950 font-black' : 'text-slate-800'}">
          ${isP1Best ? '<span class="text-emerald-700 font-black mr-1">✓</span>' : ''}${p1Str}
        </td>
        <td class="py-3 px-3 text-right font-medium ${isP2Best ? 'bg-emerald-100 text-emerald-950 font-black' : 'text-slate-800'}">
          ${isP2Best ? '<span class="text-emerald-700 font-black mr-1">✓</span>' : ''}${p2Str}
        </td>
        <td class="py-3 px-3 text-right font-medium ${isP3Best ? 'bg-emerald-100 text-emerald-950 font-black' : 'text-slate-800'}">
          ${isP3Best ? '<span class="text-emerald-700 font-black mr-1">✓</span>' : ''}${p3Str}
        </td>

        <td class="py-3 px-3 font-semibold text-slate-800 truncate max-w-[140px]">${r.proveedor_mas_barato}</td>
        <td class="py-3 px-3 text-right font-bold text-slate-900">$${r.diferencia_dinero.toLocaleString('es-AR', { minimumFractionDigits: 2 })}</td>
        <td class="py-3 px-3 text-right">
          <span class="px-2 py-0.5 rounded text-[11px] ${pctBadgeClass}" title="${r.explicacion_porcentaje}">
            ${r.diferencia_porcentaje.toFixed(2)}%
          </span>
        </td>
        <td class="py-3 px-3 text-center">
          <span class="px-2 py-0.5 rounded text-[10px] font-semibold ${
            r.present_count === 3 ? 'bg-sky-100 text-sky-800 border border-sky-200' :
            r.present_count === 2 ? 'bg-indigo-100 text-indigo-800 border border-indigo-200' :
            'bg-slate-100 text-slate-700 border border-slate-200'
          }">${r.estado_precio}</span>
        </td>
      `;
      tbody.appendChild(tr);
    });
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
  exportFile(format) {
    if (!this.comparisonResult) {
      this.showAlert('error', 'No hay resultados para exportar.');
      return;
    }
    window.location.href = `/api/export/${format}`;
  }

  exportOrder(listIdx) {
    if (!this.comparisonResult) {
      this.showAlert('error', 'No hay resultados para exportar.');
      return;
    }
    window.location.href = `/api/export/order/${listIdx}`;
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
