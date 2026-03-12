(function () {
  'use strict';

  var GRID_SIZE = 500;
  var EPS = 1e-6;

  var state = {
    profiles: [],
    selectedId: null,
    domain: { width: 0.6, height: 0.25, groundHeight: 0.006 },
    pendingFile: null,
    importModalOpen: false,
    isParamsCollapsed: false,
    camera: { x: 100, y: 600, scale: 1 },
  };

  var derived = {
    computedGeometry: [],
    tangentHeight: 0,
    parameterSet: [],
    anyOutOfBounds: false,
  };

  var drag = {
    mode: null,
    startX: 0,
    startY: 0,
    startCameraX: 0,
    startCameraY: 0,
    profileId: null,
    startWorld: null,
    startProfileX: 0,
    startProfileY: 0,
    startRotation: 0,
    startAngle: 0,
    startScaleX: 1,
    startScaleY: 1,
    scaleHandleId: null,
    startLocalMinX: 0,
    startLocalMaxX: 0,
    startLocalMinY: 0,
    startLocalMaxY: 0,
    startLocalWidth: 1,
    startLocalHeight: 1,
    fixedLocalX: 0,
    fixedLocalY: 0,
  };

  var ui = {
    canvasPane: document.getElementById('canvasPane'),
    canvas: document.getElementById('sceneCanvas'),
    hud: document.getElementById('hud'),
    domainHeight: document.getElementById('domainHeight'),
    domainWidth: document.getElementById('domainWidth'),
    domainGround: document.getElementById('domainGround'),
    fileInput: document.getElementById('fileInput'),
    profilesList: document.getElementById('profilesList'),
    propertiesContent: document.getElementById('propertiesContent'),
    paramsPanel: document.getElementById('paramsPanel'),
    paramsToggle: document.getElementById('paramsToggle'),
    paramsArrow: document.getElementById('paramsArrow'),
    paramsBody: document.getElementById('paramsBody'),
    importModal: document.getElementById('importModal'),
    previewWrap: document.getElementById('previewWrap'),
    importMainBtn: document.getElementById('importMainBtn'),
    importFlapBtn: document.getElementById('importFlapBtn'),
    importCancelBtn: document.getElementById('importCancelBtn'),
  };

  var ctx = ui.canvas.getContext('2d');
  var currentTransformHandles = null;

  function init() {
    bindUI();
    initCanvas();
    recomputeDerived();
    renderAll();
  }

  function bindUI() {
    ui.domainHeight.addEventListener('input', function (e) {
      var value = parseFloat(e.target.value);
      if (Number.isFinite(value)) {
        state.domain.height = value;
        renderLiveViews();
      }
    });

    ui.domainWidth.addEventListener('input', function (e) {
      var value = parseFloat(e.target.value);
      if (Number.isFinite(value)) {
        state.domain.width = value;
        renderLiveViews();
      }
    });

    ui.domainGround.addEventListener('input', function (e) {
      var value = parseFloat(e.target.value);
      if (Number.isFinite(value)) {
        state.domain.groundHeight = value;
        renderLiveViews();
      }
    });

    ui.fileInput.addEventListener('change', onFileSelect);

    ui.paramsToggle.addEventListener('click', function () {
      state.isParamsCollapsed = !state.isParamsCollapsed;
      renderParamsPanel();
    });

    ui.importMainBtn.addEventListener('click', function () {
      confirmImport('Main');
    });

    ui.importFlapBtn.addEventListener('click', function () {
      confirmImport('Flap');
    });

    ui.importCancelBtn.addEventListener('click', function () {
      closeImportModal();
    });

    ui.importModal.addEventListener('click', function (e) {
      if (e.target === ui.importModal) closeImportModal();
    });
  }

  function initCanvas() {
    resizeCanvas();

    var resizeObserver = new ResizeObserver(function () {
      resizeCanvas();
      renderAll();
    });
    resizeObserver.observe(ui.canvasPane);

    ui.canvas.addEventListener('mousedown', onCanvasMouseDown);
    ui.canvas.addEventListener('wheel', onCanvasWheel, { passive: false });

    window.addEventListener('mousemove', onWindowMouseMove);
    window.addEventListener('mouseup', onWindowMouseUp);
  }

  function resizeCanvas() {
    var rect = ui.canvasPane.getBoundingClientRect();
    var dpr = window.devicePixelRatio || 1;
    ui.canvas.width = Math.max(1, Math.floor(rect.width * dpr));
    ui.canvas.height = Math.max(1, Math.floor(rect.height * dpr));
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }

  function onFileSelect(e) {
    var file = e.target.files && e.target.files[0];
    if (!file) return;

    var reader = new FileReader();
    reader.onload = function (ev) {
      var content = String(ev.target && ev.target.result ? ev.target.result : '');
      var points = parseCoordsTxt(content);
      state.pendingFile = { name: file.name, content: content, points: points };
      openImportModal();
    };
    reader.readAsText(file);

    e.target.value = '';
  }

  function confirmImport(type) {
    if (!state.pendingFile) return;

    var parentId = null;
    var initialX = 0;
    var initialY = 0;

    if (type === 'Flap') {
      if (state.profiles.length > 0) {
        parentId = state.profiles[state.profiles.length - 1].id;
        initialX = 0.05;
        initialY = -0.02;
      }
    } else {
      initialY = 0;
    }

    var newProfile = {
      id: Math.random().toString(36).substring(2, 9),
      name: state.pendingFile.name,
      type: type,
      points: state.pendingFile.points,
      scaleX: 1,
      scaleY: 1,
      rotation: 0,
      x: initialX,
      y: initialY,
      parentId: parentId,
    };

    state.profiles.push(newProfile);
    state.selectedId = newProfile.id;

    closeImportModal();
    renderAll();
  }

  function openImportModal() {
    state.importModalOpen = true;
    ui.importModal.classList.remove('hidden');
    renderImportPreview();
  }

  function closeImportModal() {
    state.importModalOpen = false;
    state.pendingFile = null;
    ui.importModal.classList.add('hidden');
    ui.previewWrap.innerHTML = '';
  }

  function renderImportPreview() {
    ui.previewWrap.innerHTML = '';

    if (!state.pendingFile || state.pendingFile.points.length === 0) {
      var fallback = document.createElement('div');
      fallback.className = 'preview-fallback';
      fallback.textContent = 'Invalid Geometry';
      ui.previewWrap.appendChild(fallback);
      return;
    }

    var points = state.pendingFile.points;
    var xs = points.map(function (p) { return p.x; });
    var ys = points.map(function (p) { return p.y; });
    var minX = Math.min.apply(Math, xs);
    var maxX = Math.max.apply(Math, xs);
    var minY = Math.min.apply(Math, ys);
    var maxY = Math.max.apply(Math, ys);
    var w = maxX - minX || 1;
    var h = maxY - minY || 1;
    var padding = w * 0.1;

    var svgNS = 'http://www.w3.org/2000/svg';
    var svg = document.createElementNS(svgNS, 'svg');
    svg.setAttribute('viewBox', [minX - padding, minY - padding, w + padding * 2, h + padding * 2].join(' '));

    var polygon = document.createElementNS(svgNS, 'polygon');
    polygon.setAttribute(
      'points',
      points
        .map(function (p) {
          return p.x + ',' + p.y;
        })
        .join(' ')
    );
    polygon.setAttribute('fill', 'rgba(37, 99, 235, 0.2)');
    polygon.setAttribute('stroke', '#2563eb');
    polygon.setAttribute('stroke-width', String(w / 100));
    polygon.setAttribute('vector-effect', 'non-scaling-stroke');

    svg.appendChild(polygon);
    ui.previewWrap.appendChild(svg);

    var fileTag = document.createElement('div');
    fileTag.className = 'preview-file';
    fileTag.textContent = state.pendingFile.name;
    ui.previewWrap.appendChild(fileTag);
  }

  function recomputeDerived() {
    derived.computedGeometry = computeWorldGeometry(state.profiles, state.domain);

    var mainProfile = state.profiles.find(function (p) {
      return p.type === 'Main';
    });
    derived.tangentHeight = calculateTangentHeight(mainProfile);

    derived.parameterSet = buildParameterSet();

    derived.anyOutOfBounds = !areAllProfilesInsideDomain(derived.computedGeometry, state.domain);
  }

  function buildParameterSet() {
    var main = state.profiles.find(function (p) {
      return p.type === 'Main';
    });
    var flaps = state.profiles.filter(function (p) {
      return p.type === 'Flap';
    });

    var params = [
      { id: 'P1', name: 'Wing_Rotate', val: main ? main.rotation : 0, unit: 'deg' },
      { id: 'P2', name: 'Main_Rotate', val: main ? main.rotation : 0, unit: 'deg' },
      { id: 'P6', name: 'Main_XScale', val: main ? main.scaleX : 1, unit: '-' },
      { id: 'P7', name: 'Main_YScale', val: main ? main.scaleY : 1, unit: '-' },
    ];

    flaps.forEach(function (flap, idx) {
      var n = idx + 1;
      var base = 100 + idx * 10;
      params.push({ id: 'P' + (base + 1), name: 'Flap' + n + '_Rotate', val: flap.rotation, unit: 'deg' });
      params.push({ id: 'P' + (base + 2), name: 'Flap' + n + '_XScale', val: flap.scaleX, unit: '-' });
      params.push({ id: 'P' + (base + 3), name: 'Flap' + n + '_YScale', val: flap.scaleY, unit: '-' });
      params.push({ id: 'P' + (base + 4), name: 'Flap' + n + '_XMove', val: flap.x, unit: 'm' });
      params.push({ id: 'P' + (base + 5), name: 'Flap' + n + '_YMove', val: flap.y, unit: 'm' });
    });

    params.push({ id: 'P20', name: 'TangentLine_Main', val: derived.tangentHeight, unit: 'm', highlight: true });
    params.push({ id: 'P21', name: 'Ground_Height', val: state.domain.groundHeight, unit: 'm' });

    return params;
  }

  function renderAll() {
    recomputeDerived();
    syncDomainInputs();
    renderProfilesList();
    renderProperties();
    renderParamsPanel();
    renderHud();
    drawScene();
  }

  // Used while typing in inputs: avoids rebuilding right-side forms and losing focus.
  function renderLiveViews() {
    recomputeDerived();
    renderParamsPanel();
    renderHud();
    drawScene();
  }

  function syncDomainInputs() {
    ui.domainHeight.value = String(state.domain.height);
    ui.domainWidth.value = String(state.domain.width);
    ui.domainGround.value = String(state.domain.groundHeight);
  }

  function renderProfilesList() {
    ui.profilesList.innerHTML = '';

    if (state.profiles.length === 0) {
      var empty = document.createElement('div');
      empty.className = 'empty-note';
      empty.textContent = 'No profiles loaded.';
      ui.profilesList.appendChild(empty);
      return;
    }

    state.profiles.forEach(function (profile) {
      var card = document.createElement('div');
      card.className = 'profile-card' + (profile.id === state.selectedId ? ' selected' : '');
      card.addEventListener('click', function () {
        state.selectedId = profile.id;
        renderAll();
      });

      var main = document.createElement('div');
      main.className = 'profile-main';

      var name = document.createElement('div');
      name.className = 'profile-name';
      name.textContent = profile.name;

      var meta = document.createElement('div');
      meta.className = 'profile-meta';

      var tag = document.createElement('span');
      tag.className = 'tag ' + (profile.type === 'Main' ? 'main' : 'flap');
      tag.textContent = profile.type;

      meta.appendChild(tag);
      if (profile.parentId) {
        var attached = document.createElement('span');
        attached.textContent = 'Attached';
        meta.appendChild(attached);
      }

      main.appendChild(name);
      main.appendChild(meta);

      var delBtn = document.createElement('button');
      delBtn.className = 'delete-btn';
      delBtn.type = 'button';
      delBtn.textContent = '🗑';
      delBtn.title = 'Delete';
      delBtn.addEventListener('click', function (e) {
        e.stopPropagation();
        removeProfile(profile.id);
      });

      card.appendChild(main);
      card.appendChild(delBtn);

      ui.profilesList.appendChild(card);
    });
  }

  function renderProperties() {
    ui.propertiesContent.innerHTML = '';

    var selected = getSelectedProfile();

    if (!selected) {
      var empty = document.createElement('div');
      empty.className = 'empty-note';
      empty.style.marginTop = '18px';
      empty.style.fontStyle = 'normal';
      empty.textContent = 'Select a profile to edit properties.';
      ui.propertiesContent.appendChild(empty);
      return;
    }

    var grid = document.createElement('div');
    grid.className = 'props-grid';

    function addField(label, value, step, onInput, full) {
      var wrap = document.createElement('label');
      wrap.className = 'prop-field' + (full ? ' full' : '');

      var text = document.createElement('span');
      text.textContent = label;

      var input = document.createElement('input');
      input.type = 'number';
      input.step = step;
      input.value = String(value);
      input.addEventListener('input', function (e) {
        var v = parseFloat(e.target.value);
        if (Number.isFinite(v)) {
          onInput(v);
          renderLiveViews();
        }
      });

      wrap.appendChild(text);
      wrap.appendChild(input);
      grid.appendChild(wrap);
    }

    var nameWrap = document.createElement('div');
    nameWrap.className = 'full';

    var nameLabel = document.createElement('div');
    nameLabel.className = 'prop-label';
    nameLabel.textContent = 'Name';

    var nameRead = document.createElement('div');
    nameRead.className = 'profile-name-read';
    nameRead.textContent = selected.name;

    nameWrap.appendChild(nameLabel);
    nameWrap.appendChild(nameRead);
    grid.appendChild(nameWrap);

    addField('Rotation (deg)', selected.rotation, '0.1', function (v) {
      updateProfile(selected.id, { rotation: v });
    }, true);

    addField('Scale X', selected.scaleX, '0.01', function (v) {
      updateProfile(selected.id, { scaleX: v });
    }, false);

    addField('Scale Y', selected.scaleY, '0.01', function (v) {
      updateProfile(selected.id, { scaleY: v });
    }, false);

    if (selected.type === 'Flap') {
      addField('Dist X', selected.x, '0.001', function (v) {
        updateProfile(selected.id, { x: v });
      }, false);

      addField('Dist Y', selected.y, '0.001', function (v) {
        updateProfile(selected.id, { y: v });
      }, false);
    } else {
      var note = document.createElement('div');
      note.className = 'small-note full';
      note.textContent = 'Main profile position is controlled by Ground Height.';
      grid.appendChild(note);
    }

    ui.propertiesContent.appendChild(grid);
  }

  function renderParamsPanel() {
    ui.paramsPanel.classList.toggle('collapsed', state.isParamsCollapsed);
    ui.paramsArrow.textContent = state.isParamsCollapsed ? '▲' : '▼';
    ui.paramsBody.style.display = state.isParamsCollapsed ? 'none' : 'flex';

    if (state.isParamsCollapsed) return;

    ui.paramsBody.innerHTML = '';

    derived.parameterSet.forEach(function (param) {
      var card = document.createElement('div');
      card.className = 'param-card' + (param.highlight ? ' highlight' : '');

      var id = document.createElement('div');
      id.className = 'param-id';
      id.textContent = param.id;

      var name = document.createElement('div');
      name.className = 'param-name';
      name.title = param.name;
      name.textContent = param.name;

      var val = document.createElement('div');
      val.className = 'param-val';
      var text = typeof param.val === 'number' ? param.val.toFixed(4) : String(param.val);
      val.textContent = text;

      var unit = document.createElement('span');
      unit.className = 'param-unit';
      unit.textContent = param.unit;
      val.appendChild(unit);

      card.appendChild(id);
      card.appendChild(name);
      card.appendChild(val);

      ui.paramsBody.appendChild(card);
    });
  }

  function renderHud() {
    var warn = derived.anyOutOfBounds ? '<div class="warn">⚠ OUT OF BOUNDS</div>' : '';
    ui.hud.innerHTML =
      '<div class="title">Display Info</div>' +
      '<div>Zoom: ' + state.camera.scale.toFixed(2) + 'x</div>' +
      '<div>Grid: Fixed (Domain + 2m)</div>' +
      '<div>Ground: ' + state.domain.groundHeight.toFixed(4) + 'm (Tangent)</div>' +
      warn;
  }

  function drawScene() {
    var rect = ui.canvasPane.getBoundingClientRect();
    var width = rect.width;
    var height = rect.height;

    ctx.setTransform(window.devicePixelRatio || 1, 0, 0, window.devicePixelRatio || 1, 0, 0);
    ctx.clearRect(0, 0, width, height);

    ctx.fillStyle = '#e2e8f0';
    ctx.fillRect(0, 0, width, height);

    drawGridAndDomain();
    drawProfiles();
    drawGridLabels();
    drawSelectionOverlay();
  }

  function drawGridAndDomain() {
    var scale = state.camera.scale;
    applyWorldTransform();

    var margin = 2.0;
    var startX = -margin;
    var endX = state.domain.width + margin;
    var startY = -margin;
    var endY = state.domain.height + margin;
    var step = 0.1;

    ctx.fillStyle = '#f8fafc';
    ctx.fillRect(startX, startY, endX - startX, endY - startY);

    var numStepsX = Math.round((endX - startX) / step);
    for (var i = 0; i <= numStepsX; i += 1) {
      var x = startX + i * step;
      var isAxisX = Math.abs(x) < 0.001;
      var isMajorX = Math.abs(x % 0.5) < 0.001;

      ctx.beginPath();
      ctx.moveTo(x, startY);
      ctx.lineTo(x, endY);
      ctx.strokeStyle = isAxisX ? '#334155' : isMajorX ? '#cbd5e1' : '#e2e8f0';
      ctx.lineWidth = (isAxisX ? 2 : 1) / (scale * GRID_SIZE);
      ctx.stroke();
    }

    var numStepsY = Math.round((endY - startY) / step);
    for (var j = 0; j <= numStepsY; j += 1) {
      var y = startY + j * step;
      var isAxisY = Math.abs(y) < 0.001;
      var isMajorY = Math.abs(y % 0.5) < 0.001;

      ctx.beginPath();
      ctx.moveTo(startX, y);
      ctx.lineTo(endX, y);
      ctx.strokeStyle = isAxisY ? '#334155' : isMajorY ? '#cbd5e1' : '#e2e8f0';
      ctx.lineWidth = (isAxisY ? 2 : 1) / (scale * GRID_SIZE);
      ctx.stroke();
    }

    ctx.beginPath();
    ctx.rect(0, 0, state.domain.width, state.domain.height);
    ctx.setLineDash([15 / (scale * GRID_SIZE), 15 / (scale * GRID_SIZE)]);
    ctx.strokeStyle = derived.anyOutOfBounds ? 'red' : '#22c55e';
    ctx.lineWidth = 3 / (scale * GRID_SIZE);
    ctx.stroke();
    ctx.setLineDash([]);

    ctx.setTransform(window.devicePixelRatio || 1, 0, 0, window.devicePixelRatio || 1, 0, 0);
  }

  function drawProfiles() {
    applyWorldTransform();

    var pxToWorld = 1 / (state.camera.scale * GRID_SIZE);

    derived.computedGeometry.forEach(function (geo) {
      var profile = getProfileById(geo.id);
      if (!profile || geo.worldPoints.length === 0) return;

      ctx.beginPath();
      geo.worldPoints.forEach(function (pt, idx) {
        if (idx === 0) ctx.moveTo(pt.x, pt.y);
        else ctx.lineTo(pt.x, pt.y);
      });
      ctx.closePath();

      var isSelected = state.selectedId === geo.id;
      ctx.fillStyle = profile.type === 'Main' ? 'rgba(37, 99, 235, 0.2)' : 'rgba(5, 150, 105, 0.2)';
      ctx.strokeStyle = profile.type === 'Main' ? '#2563eb' : '#059669';
      ctx.lineWidth = (isSelected ? 3 : 1.5) * pxToWorld;
      ctx.fill();
      ctx.stroke();

      var center = getProfileCenter(geo.worldPoints);

      ctx.beginPath();
      ctx.arc(center.x, center.y, 6 * pxToWorld, 0, Math.PI * 2);
      ctx.fillStyle = 'orange';
      ctx.fill();
      ctx.lineWidth = 1 * pxToWorld;
      ctx.strokeStyle = '#ffffff';
      ctx.stroke();

      ctx.beginPath();
      ctx.arc(geo.worldTransform.x, geo.worldTransform.y, 3 * pxToWorld, 0, Math.PI * 2);
      ctx.fillStyle = 'rgba(220, 38, 38, 0.5)';
      ctx.fill();
    });

    ctx.setTransform(window.devicePixelRatio || 1, 0, 0, window.devicePixelRatio || 1, 0, 0);
  }

  function drawGridLabels() {
    var margin = 2.0;
    var startX = -margin;
    var endX = state.domain.width + margin;
    var startY = -margin;
    var endY = state.domain.height + margin;
    var step = 0.1;

    ctx.fillStyle = '#94a3b8';
    ctx.font = '10px ui-monospace, Menlo, Consolas, monospace';

    var numStepsX = Math.round((endX - startX) / step);
    for (var i = 0; i <= numStepsX; i += 1) {
      var x = startX + i * step;
      var sx = worldToScreenX(x);
      var sy = worldToScreenY(startY);
      ctx.fillText(String((x * 1000).toFixed(0)), sx + 2, sy - 8);
    }

    var numStepsY = Math.round((endY - startY) / step);
    for (var j = 0; j <= numStepsY; j += 1) {
      var y = startY + j * step;
      var sx2 = worldToScreenX(startX);
      var sy2 = worldToScreenY(y);
      ctx.fillText(String((y * 1000).toFixed(0)), sx2 + 5, sy2 - 2);
    }
  }

  function drawSelectionOverlay() {
    currentTransformHandles = null;

    var selectedGeo = getSelectedGeometry();
    if (!selectedGeo || selectedGeo.worldPoints.length === 0) return;

    var bbox = getBounds(selectedGeo.worldPoints);
    var nw = worldToScreen(bbox.minX, bbox.maxY);
    var ne = worldToScreen(bbox.maxX, bbox.maxY);
    var se = worldToScreen(bbox.maxX, bbox.minY);
    var sw = worldToScreen(bbox.minX, bbox.minY);

    ctx.save();
    ctx.strokeStyle = '#f59e0b';
    ctx.lineWidth = 1;
    ctx.setLineDash([6, 4]);
    ctx.beginPath();
    ctx.moveTo(nw.x, nw.y);
    ctx.lineTo(ne.x, ne.y);
    ctx.lineTo(se.x, se.y);
    ctx.lineTo(sw.x, sw.y);
    ctx.closePath();
    ctx.stroke();
    ctx.setLineDash([]);

    var handleSize = 10;
    var handles = [
      { id: 'nw', x: nw.x, y: nw.y },
      { id: 'ne', x: ne.x, y: ne.y },
      { id: 'se', x: se.x, y: se.y },
      { id: 'sw', x: sw.x, y: sw.y },
    ];

    ctx.fillStyle = '#ffffff';
    ctx.strokeStyle = '#f59e0b';

    handles.forEach(function (h) {
      ctx.beginPath();
      ctx.rect(h.x - handleSize / 2, h.y - handleSize / 2, handleSize, handleSize);
      ctx.fill();
      ctx.stroke();
    });

    var rotateBase = worldToScreen((bbox.minX + bbox.maxX) * 0.5, bbox.maxY);
    var rotateHandle = { x: rotateBase.x, y: rotateBase.y - 34 };

    ctx.beginPath();
    ctx.moveTo(rotateBase.x, rotateBase.y);
    ctx.lineTo(rotateHandle.x, rotateHandle.y);
    ctx.stroke();

    ctx.beginPath();
    ctx.arc(rotateHandle.x, rotateHandle.y, 7, 0, Math.PI * 2);
    ctx.fill();
    ctx.stroke();

    ctx.restore();

    currentTransformHandles = {
      scale: handles,
      rotate: rotateHandle,
    };
  }

  function onCanvasWheel(e) {
    e.preventDefault();

    var scaleBy = 1.1;
    var oldScale = state.camera.scale;
    var newAbsScale = e.deltaY > 0 ? oldScale / scaleBy : oldScale * scaleBy;

    if (newAbsScale < 0.1 || newAbsScale > 50) return;

    var rect = ui.canvas.getBoundingClientRect();
    var pointerX = e.clientX - rect.left;
    var pointerY = e.clientY - rect.top;

    var mousePointTo = {
      x: (pointerX - state.camera.x) / oldScale,
      y: (pointerY - state.camera.y) / oldScale,
    };

    state.camera.scale = newAbsScale;
    state.camera.x = pointerX - mousePointTo.x * newAbsScale;
    state.camera.y = pointerY - mousePointTo.y * newAbsScale;

    renderAll();
  }

  function onCanvasMouseDown(e) {
    var rect = ui.canvas.getBoundingClientRect();
    var sx = e.clientX - rect.left;
    var sy = e.clientY - rect.top;
    var world = screenToWorld(sx, sy);

    if (state.selectedId && currentTransformHandles) {
      var rotateHit = hitRotateHandle(sx, sy);
      if (rotateHit) {
        startRotateTransform(world);
        return;
      }

      var scaleHit = hitScaleHandle(sx, sy);
      if (scaleHit) {
        startScaleTransform(scaleHit, world);
        return;
      }
    }

    var centerHit = hitCenterHandle(sx, sy);
    if (centerHit) {
      state.selectedId = centerHit.id;
      var selectedProfile = getSelectedProfile();
      drag.mode = 'profile';
      drag.profileId = centerHit.id;
      drag.startWorld = world;
      drag.startProfileX = selectedProfile ? selectedProfile.x : 0;
      drag.startProfileY = selectedProfile ? selectedProfile.y : 0;
      renderAll();
      return;
    }

    var polygonHit = hitPolygon(world.x, world.y);
    if (polygonHit) {
      state.selectedId = polygonHit.id;
      renderAll();
      return;
    }

    state.selectedId = null;
    drag.mode = 'stage';
    drag.startX = sx;
    drag.startY = sy;
    drag.startCameraX = state.camera.x;
    drag.startCameraY = state.camera.y;
    renderAll();
  }

  function onWindowMouseMove(e) {
    if (!drag.mode) return;

    var rect = ui.canvas.getBoundingClientRect();
    var sx = e.clientX - rect.left;
    var sy = e.clientY - rect.top;

    if (drag.mode === 'stage') {
      state.camera.x = drag.startCameraX + (sx - drag.startX);
      state.camera.y = drag.startCameraY + (sy - drag.startY);
      renderAll();
      return;
    }

    if (drag.mode === 'profile') {
      var profile = getProfileById(drag.profileId);
      if (!profile) return;

      if (profile.type !== 'Main') {
        var world = screenToWorld(sx, sy);
        var dx = world.x - drag.startWorld.x;
        var dy = world.y - drag.startWorld.y;
        profile.x = drag.startProfileX + dx;
        profile.y = drag.startProfileY + dy;
        renderAll();
      }
      return;
    }

    if (drag.mode === 'rotate') {
      var profileR = getProfileById(drag.profileId);
      if (!profileR) return;

      var worldR = screenToWorld(sx, sy);
      var originR = getProfileWorldOrigin(drag.profileId);
      if (!originR) return;

      var currentAngle = Math.atan2(worldR.y - originR.y, worldR.x - originR.x);
      var delta = ((currentAngle - drag.startAngle) * 180) / Math.PI;
      profileR.rotation = drag.startRotation + delta;
      renderAll();
      return;
    }

    if (drag.mode === 'scale') {
      var profileS = getProfileById(drag.profileId);
      if (!profileS) return;

      var worldS = screenToWorld(sx, sy);
      var originS = getProfileWorldOrigin(drag.profileId);
      if (!originS) return;

      var local = rotatePoint(worldS.x - originS.x, worldS.y - originS.y, -drag.startRotation);

      var handleId = drag.scaleHandleId;
      var minX = drag.fixedLocalX;
      var maxX = drag.fixedLocalX;
      var minY = drag.fixedLocalY;
      var maxY = drag.fixedLocalY;

      if (handleId === 'nw' || handleId === 'sw') {
        minX = local.x;
      } else {
        maxX = local.x;
      }

      if (handleId === 'nw' || handleId === 'ne') {
        maxY = local.y;
      } else {
        minY = local.y;
      }

      var newWidth = maxX - minX;
      var newHeight = maxY - minY;

      var factorX = Math.abs(newWidth) / Math.max(drag.startLocalWidth, EPS);
      var factorY = Math.abs(newHeight) / Math.max(drag.startLocalHeight, EPS);

      var newScaleX = drag.startScaleX * factorX;
      var newScaleY = drag.startScaleY * factorY;

      if (!Number.isFinite(newScaleX)) newScaleX = drag.startScaleX;
      if (!Number.isFinite(newScaleY)) newScaleY = drag.startScaleY;

      profileS.scaleX = clamp(newScaleX, 0.02, 50);
      profileS.scaleY = clamp(newScaleY, 0.02, 50);
      renderAll();
    }
  }

  function onWindowMouseUp() {
    drag.mode = null;
    drag.profileId = null;
    drag.scaleHandleId = null;
  }

  function startRotateTransform(world) {
    var profile = getSelectedProfile();
    if (!profile) return;

    var origin = getProfileWorldOrigin(profile.id);
    if (!origin) return;

    drag.mode = 'rotate';
    drag.profileId = profile.id;
    drag.startRotation = profile.rotation;
    drag.startAngle = Math.atan2(world.y - origin.y, world.x - origin.x);
  }

  function startScaleTransform(handle, world) {
    var profile = getSelectedProfile();
    if (!profile) return;

    var origin = getProfileWorldOrigin(profile.id);
    if (!origin) return;

    var geo = getSelectedGeometry();
    if (!geo) return;

    var localPoints = geo.worldPoints.map(function (pt) {
      return rotatePoint(pt.x - origin.x, pt.y - origin.y, -profile.rotation);
    });

    var localBounds = getBounds(localPoints);

    var fixedLocalX = handle.id === 'nw' || handle.id === 'sw' ? localBounds.maxX : localBounds.minX;
    var fixedLocalY = handle.id === 'nw' || handle.id === 'ne' ? localBounds.minY : localBounds.maxY;

    drag.mode = 'scale';
    drag.profileId = profile.id;
    drag.scaleHandleId = handle.id;
    drag.startScaleX = profile.scaleX;
    drag.startScaleY = profile.scaleY;
    drag.startRotation = profile.rotation;
    drag.startLocalMinX = localBounds.minX;
    drag.startLocalMaxX = localBounds.maxX;
    drag.startLocalMinY = localBounds.minY;
    drag.startLocalMaxY = localBounds.maxY;
    drag.startLocalWidth = Math.max(localBounds.maxX - localBounds.minX, EPS);
    drag.startLocalHeight = Math.max(localBounds.maxY - localBounds.minY, EPS);
    drag.fixedLocalX = fixedLocalX;
    drag.fixedLocalY = fixedLocalY;
  }

  function hitRotateHandle(sx, sy) {
    if (!currentTransformHandles || !currentTransformHandles.rotate) return false;
    var h = currentTransformHandles.rotate;
    var dx = sx - h.x;
    var dy = sy - h.y;
    return dx * dx + dy * dy <= 10 * 10;
  }

  function hitScaleHandle(sx, sy) {
    if (!currentTransformHandles) return null;
    for (var i = 0; i < currentTransformHandles.scale.length; i += 1) {
      var h = currentTransformHandles.scale[i];
      if (Math.abs(sx - h.x) <= 7 && Math.abs(sy - h.y) <= 7) return h;
    }
    return null;
  }

  function hitCenterHandle(sx, sy) {
    for (var i = derived.computedGeometry.length - 1; i >= 0; i -= 1) {
      var geo = derived.computedGeometry[i];
      var center = getProfileCenter(geo.worldPoints);
      var screen = worldToScreen(center.x, center.y);
      var dx = sx - screen.x;
      var dy = sy - screen.y;
      if (dx * dx + dy * dy <= 9 * 9) return { id: geo.id };
    }
    return null;
  }

  function hitPolygon(worldX, worldY) {
    for (var i = derived.computedGeometry.length - 1; i >= 0; i -= 1) {
      var geo = derived.computedGeometry[i];
      if (pointInPolygon(worldX, worldY, geo.worldPoints)) {
        return { id: geo.id };
      }
    }
    return null;
  }

  function applyWorldTransform() {
    var dpr = window.devicePixelRatio || 1;
    var s = state.camera.scale * GRID_SIZE;
    ctx.setTransform(s * dpr, 0, 0, -s * dpr, state.camera.x * dpr, state.camera.y * dpr);
  }

  function worldToScreen(x, y) {
    return {
      x: worldToScreenX(x),
      y: worldToScreenY(y),
    };
  }

  function worldToScreenX(x) {
    return x * GRID_SIZE * state.camera.scale + state.camera.x;
  }

  function worldToScreenY(y) {
    return -y * GRID_SIZE * state.camera.scale + state.camera.y;
  }

  function screenToWorld(sx, sy) {
    return {
      x: (sx - state.camera.x) / (GRID_SIZE * state.camera.scale),
      y: -(sy - state.camera.y) / (GRID_SIZE * state.camera.scale),
    };
  }

  function getSelectedProfile() {
    return state.profiles.find(function (p) {
      return p.id === state.selectedId;
    }) || null;
  }

  function getProfileById(id) {
    return (
      state.profiles.find(function (p) {
        return p.id === id;
      }) || null
    );
  }

  function getSelectedGeometry() {
    return (
      derived.computedGeometry.find(function (g) {
        return g.id === state.selectedId;
      }) || null
    );
  }

  function getProfileWorldOrigin(id) {
    var geo = derived.computedGeometry.find(function (g) {
      return g.id === id;
    });
    return geo ? geo.worldTransform : null;
  }

  function getProfileCenter(points) {
    var xs = points.map(function (p) { return p.x; });
    var ys = points.map(function (p) { return p.y; });
    return {
      x: (Math.min.apply(Math, xs) + Math.max.apply(Math, xs)) * 0.5,
      y: (Math.min.apply(Math, ys) + Math.max.apply(Math, ys)) * 0.5,
    };
  }

  function getBounds(points) {
    var xs = points.map(function (p) { return p.x; });
    var ys = points.map(function (p) { return p.y; });
    return {
      minX: Math.min.apply(Math, xs),
      maxX: Math.max.apply(Math, xs),
      minY: Math.min.apply(Math, ys),
      maxY: Math.max.apply(Math, ys),
    };
  }

  function updateProfile(id, changes) {
    state.profiles = state.profiles.map(function (p) {
      return p.id === id ? Object.assign({}, p, changes) : p;
    });
  }

  function removeProfile(id) {
    state.profiles = state.profiles.filter(function (p) {
      return p.id !== id && p.parentId !== id;
    });
    if (state.selectedId === id) state.selectedId = null;
    renderAll();
  }

  function parseCoordsTxt(text) {
    var lines = text.split(/\r?\n/);
    var pts = [];

    lines.forEach(function (line) {
      var l = line.trim();
      if (!l || l.charAt(0) === '#') return;

      var parts = l.split(/\s+/);
      if (parts.length < 2) return;

      var xStr = parts[0];
      var yStr = parts[1];

      if (parts.length >= 4) {
        xStr = parts[2];
        yStr = parts[3];
      } else if (parts.length === 3) {
        xStr = parts[1];
        yStr = parts[2];
      }

      var x = parseFloat((xStr || '0').replace(',', '.'));
      var y = parseFloat((yStr || '0').replace(',', '.'));

      if (Number.isFinite(x) && Number.isFinite(y)) {
        pts.push({ x: x, y: y });
      }
    });

    return pts;
  }

  function getTrailingEdgeIndex(points) {
    if (!points.length) return 0;
    var maxIdx = 0;
    var maxX = -Infinity;

    points.forEach(function (p, i) {
      if (p.x > maxX) {
        maxX = p.x;
        maxIdx = i;
      }
    });

    return maxIdx;
  }

  function getLeadingEdgeIndex(points) {
    if (!points.length) return 0;
    var minIdx = 0;
    var minX = Infinity;

    points.forEach(function (p, i) {
      if (p.x < minX) {
        minX = p.x;
        minIdx = i;
      }
    });

    return minIdx;
  }

  function getClosestToOriginIndex(points) {
    if (!points.length) return 0;
    var minIdx = 0;
    var minDistSq = Infinity;

    points.forEach(function (p, i) {
      var dSq = p.x * p.x + p.y * p.y;
      if (dSq < minDistSq) {
        minDistSq = dSq;
        minIdx = i;
      }
    });

    return minIdx;
  }

  function transformPoint(p, ox, oy, angleDeg, sx, sy) {
    var rad = (angleDeg * Math.PI) / 180;
    var cos = Math.cos(rad);
    var sin = Math.sin(rad);

    var sxVal = p.x * sx;
    var syVal = p.y * sy;

    var rx = sxVal * cos - syVal * sin;
    var ry = sxVal * sin + syVal * cos;

    return {
      x: rx + ox,
      y: ry + oy,
    };
  }

  function computeWorldGeometry(profiles, domain) {
    var computed = {};

    function getParent(pid) {
      return pid ? computed[pid] : null;
    }

    function getDepth(profile, depth) {
      var d = depth || 0;
      if (!profile.parentId) return d;
      var parent = profiles.find(function (pr) {
        return pr.id === profile.parentId;
      });
      if (!parent) return d;
      return getDepth(parent, d + 1);
    }

    var sortedProfiles = profiles.slice().sort(function (a, b) {
      return getDepth(a, 0) - getDepth(b, 0);
    });

    sortedProfiles.forEach(function (p) {
      var worldOriginX = 0;
      var worldOriginY = 0;
      var worldRotation = 0;

      var teIndex = getTrailingEdgeIndex(p.points);
      var leIndex = getLeadingEdgeIndex(p.points);

      if (p.type === 'Main') {
        worldRotation = p.rotation;

        var relativePoints = p.points.map(function (pt) {
          return transformPoint(pt, 0, 0, worldRotation, p.scaleX, p.scaleY);
        });

        var localMinX = Infinity;
        var localMinY = Infinity;
        relativePoints.forEach(function (pt) {
          if (pt.x < localMinX) localMinX = pt.x;
          if (pt.y < localMinY) localMinY = pt.y;
        });
        if (!Number.isFinite(localMinX)) localMinX = 0;
        if (!Number.isFinite(localMinY)) localMinY = 0;

        // Keep the Main profile fully visible from the leading edge (front side).
        worldOriginX = -localMinX;
        worldOriginY = domain.groundHeight - localMinY;
      } else {
        var parent = getParent(p.parentId);
        if (parent) {
          worldOriginX = parent.trailingEdgeWorld.x + p.x;
          worldOriginY = parent.trailingEdgeWorld.y + p.y;
          worldRotation = p.rotation;
        } else {
          worldOriginX = p.x;
          worldOriginY = p.y;
          worldRotation = p.rotation;
        }
      }

      var worldPoints = p.points.map(function (pt) {
        return transformPoint(pt, worldOriginX, worldOriginY, worldRotation, p.scaleX, p.scaleY);
      });

      var teWorld = transformPoint(p.points[teIndex], worldOriginX, worldOriginY, worldRotation, p.scaleX, p.scaleY);
      var leWorld = transformPoint(p.points[leIndex], worldOriginX, worldOriginY, worldRotation, p.scaleX, p.scaleY);

      var minY = Infinity;
      worldPoints.forEach(function (pt) {
        if (pt.y < minY) minY = pt.y;
      });

      computed[p.id] = {
        id: p.id,
        worldPoints: worldPoints,
        worldTransform: { x: worldOriginX, y: worldOriginY, rotation: worldRotation },
        trailingEdgeWorld: teWorld,
        leadingEdgeWorld: leWorld,
        minYWorld: minY,
      };
    });

    return Object.keys(computed).map(function (k) {
      return computed[k];
    });
  }

  function calculateTangentHeight(profile) {
    if (!profile || !profile.points.length) return 0;

    var refIndex = getClosestToOriginIndex(profile.points);
    var sX = profile.scaleX;
    var sY = profile.scaleY;
    var rad = (profile.rotation * Math.PI) / 180;
    var cos = Math.cos(rad);
    var sin = Math.sin(rad);

    var yRef = 0;
    var yMin = Infinity;

    profile.points.forEach(function (p, i) {
      var xScaled = p.x * sX;
      var yScaled = p.y * sY;
      var yTransformed = xScaled * sin + yScaled * cos;

      if (i === refIndex) yRef = yTransformed;
      if (yTransformed < yMin) yMin = yTransformed;
    });

    return yRef - yMin;
  }

  function rotatePoint(x, y, angleDeg) {
    var rad = (angleDeg * Math.PI) / 180;
    var cos = Math.cos(rad);
    var sin = Math.sin(rad);
    return {
      x: x * cos - y * sin,
      y: x * sin + y * cos,
    };
  }

  function pointInPolygon(x, y, polygon) {
    var inside = false;
    for (var i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
      var xi = polygon[i].x;
      var yi = polygon[i].y;
      var xj = polygon[j].x;
      var yj = polygon[j].y;

      var intersect = yi > y !== yj > y && x < ((xj - xi) * (y - yi)) / (yj - yi + EPS) + xi;
      if (intersect) inside = !inside;
    }
    return inside;
  }

  function clamp(value, min, max) {
    return Math.min(max, Math.max(min, value));
  }

  function isPointOutOfBounds(pt, domain) {
    if (!Number.isFinite(domain.width) || !Number.isFinite(domain.height)) return true;
    if (!pt || !Number.isFinite(pt.x) || !Number.isFinite(pt.y)) return true;
    return pt.x < 0 || pt.x > domain.width || pt.y < 0 || pt.y > domain.height;
  }

  function areAllProfilesInsideDomain(computedGeometry, domain) {
    if (!Number.isFinite(domain.width) || !Number.isFinite(domain.height)) return false;
    if (domain.width < 0 || domain.height < 0) return false;

    for (var i = 0; i < computedGeometry.length; i += 1) {
      var geo = computedGeometry[i];
      if (!geo || !geo.worldPoints || geo.worldPoints.length === 0) continue;

      var b = getBounds(geo.worldPoints);
      if (
        !Number.isFinite(b.minX) ||
        !Number.isFinite(b.maxX) ||
        !Number.isFinite(b.minY) ||
        !Number.isFinite(b.maxY)
      ) {
        return false;
      }

      if (b.minX < 0 || b.maxX > domain.width || b.minY < 0 || b.maxY > domain.height) {
        return false;
      }
    }

    return true;
  }


  window.loadProfileFromPython = function(filename, content) {
      var points = parseCoordsTxt(content);
      state.pendingFile = { name: filename, content: content, points: points };
      // Piccolo delay per assicurarsi che il focus sia tornato alla pagina
      setTimeout(function() {
          openImportModal();
      }, 100);
  };

  init();
})();
