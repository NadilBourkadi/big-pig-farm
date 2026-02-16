// Verify data was loaded
if (typeof DATA === 'undefined') {
    document.body.innerHTML = '<div style="padding:40px;color:#e94560;font-size:16px;">'
        + 'Missing sprite_data.js &mdash; run <code>poetry run python tools/sprite_editor.py export</code> first.</div>';
    throw new Error('sprite_data.js not loaded');
}

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------
let currentGroup = null;   // e.g. "pig_adult"
let currentKey = null;     // e.g. "idle_right"
let currentPaletteName = null; // e.g. "BLACK"
let currentBrush = null;   // palette key string or null for transparent
let currentTool = 'paint'; // paint, erase, pick, fill, select
let cellSize = 20;
let showGrid = true;
let pinnedOverlay = null; // {group, key} or null
let overlayOpacity = 0.55;
let isPainting = false;
let lastPaintedCell = null;
let strokeStarted = false; // true once first pixel changed during a drag

// Working copy of all sprites (mutated on edit)
const sprites = JSON.parse(JSON.stringify(DATA.sprites));

// Dirty tracking: set of "group/key" strings
const dirtySprites = new Set();

// Undo/redo per sprite
// undoStacks["group/key"] = [{pixels: ...}, ...]
const undoStacks = {};
const redoStacks = {};

// Selection state (for select tool)
let selection = null;      // {x1, y1, x2, y2} normalised rect, or null
let selectionStart = null; // {x, y} drag start
let isSelecting = false;
let selectionBuffer = null; // 2D pixel array — floating content that moves with the selection

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
function spriteId(group, key) { return `${group}/${key}`; }

function getPixels() {
    if (!currentGroup || !currentKey) return null;
    return sprites[currentGroup][currentKey].pixels;
}

function getPalette() {
    if (!currentGroup) return {};
    if (currentGroup.startsWith('indicator')) {
        return DATA.palettes.indicator[currentKey] || {};
    }
    if (currentGroup.startsWith('facility')) {
        // Determine facility type from the sprite key
        const ftype = currentKey.replace(/_empty$/, '').replace(/_full$/, '');
        return DATA.palettes.facility[ftype] || {};
    }
    return DATA.palettes.pig[currentPaletteName] || {};
}

function getPaletteKeys() {
    if (!currentGroup) return [];
    if (currentGroup.startsWith('indicator')) {
        return DATA.palette_keys.indicator[currentKey] || [];
    }
    if (currentGroup.startsWith('facility')) {
        const ftype = currentKey.replace(/_empty$/, '').replace(/_full$/, '');
        return DATA.palette_keys.facility[ftype] || [];
    }
    return DATA.palette_keys.pig || [];
}

function getAllPigPaletteNames() {
    return Object.keys(DATA.palettes.pig);
}

function getFacilityType(key) {
    // Strip state suffixes to get base facility type
    return key.replace(/_empty$/, '').replace(/_full$/, '');
}

// ---------------------------------------------------------------------------
// Sprite list
// ---------------------------------------------------------------------------
function buildSpriteTree() {
    const tree = document.getElementById('sprite-tree');
    tree.innerHTML = '';

    const groupLabels = {
        pig_adult: 'Pig Adult',
        pig_baby: 'Pig Baby',
        pig_far_adult: 'Pig Far Adult',
        pig_far_baby: 'Pig Far Baby',
        pig_adult_close: 'Pig Adult Close',
        pig_baby_close: 'Pig Baby Close',
        facility_normal: 'Facility Normal',
        facility_far: 'Facility Far',
        facility_close: 'Facility Close',
        indicator_normal: 'Indicator Normal',
        indicator_close: 'Indicator Close',
    };

    for (const [group, label] of Object.entries(groupLabels)) {
        if (!sprites[group] || Object.keys(sprites[group]).length === 0) continue;

        const groupDiv = document.createElement('div');
        groupDiv.className = 'sprite-group';

        const header = document.createElement('div');
        header.className = 'sprite-group-header';
        header.textContent = label;
        header.onclick = () => {
            const items = groupDiv.querySelector('.sprite-items');
            items.style.display = items.style.display === 'none' ? '' : 'none';
        };
        groupDiv.appendChild(header);

        const items = document.createElement('div');
        items.className = 'sprite-items';

        // Sort keys so animation frames group together (walking_right_1, _2 adjacent)
        const sortedKeys = Object.keys(sprites[group]).sort((a, b) => {
            const baseA = a.replace(/_\d+$/, '');
            const baseB = b.replace(/_\d+$/, '');
            if (baseA !== baseB) return baseA.localeCompare(baseB);
            const numA = (a.match(/_(\d+)$/) || [, '0'])[1];
            const numB = (b.match(/_(\d+)$/) || [, '0'])[1];
            return parseInt(numA) - parseInt(numB);
        });

        for (const key of sortedKeys) {
            const item = document.createElement('div');
            item.className = 'sprite-item';
            item.dataset.group = group;
            item.dataset.key = key;
            item.textContent = key;
            if (dirtySprites.has(spriteId(group, key))) {
                item.classList.add('dirty');
            }
            item.onclick = () => selectSprite(group, key);
            items.appendChild(item);
        }

        groupDiv.appendChild(items);
        tree.appendChild(groupDiv);
    }
}

function selectSprite(group, key) {
    currentGroup = group;
    currentKey = key;
    selection = null;
    selectionStart = null;
    isSelecting = false;
    selectionBuffer = null;

    // Update active class
    document.querySelectorAll('.sprite-item').forEach(el => {
        el.classList.toggle('active',
            el.dataset.group === group && el.dataset.key === key);
    });

    // Update palette selector and reset brush if it doesn't exist in new palette
    updatePaletteSelect();
    const validKeys = getPaletteKeys();
    if (currentBrush !== null && !validKeys.includes(currentBrush)) {
        currentBrush = validKeys[0] || null;
    }
    buildPalettePanel();
    renderGrid();
    renderPreview();
    updateInfo();
}

// ---------------------------------------------------------------------------
// Palette selector
// ---------------------------------------------------------------------------
function updatePaletteSelect() {
    const sel = document.getElementById('palette-select');
    sel.innerHTML = '';

    if (currentGroup && currentGroup.startsWith('indicator')) {
        const opt = document.createElement('option');
        opt.value = currentKey;
        opt.textContent = currentKey;
        sel.appendChild(opt);
        currentPaletteName = currentKey;
    } else if (currentGroup && currentGroup.startsWith('facility')) {
        const ftype = getFacilityType(currentKey);
        const opt = document.createElement('option');
        opt.value = ftype;
        opt.textContent = ftype.replace(/_/g, ' ');
        sel.appendChild(opt);
        currentPaletteName = ftype;
    } else {
        const names = getAllPigPaletteNames();
        for (const name of names) {
            const opt = document.createElement('option');
            opt.value = name;
            opt.textContent = name;
            if (name === currentPaletteName) opt.selected = true;
            sel.appendChild(opt);
        }
        if (!names.includes(currentPaletteName)) currentPaletteName = names[0] || null;
        sel.value = currentPaletteName;
    }
}

document.getElementById('palette-select').addEventListener('change', (e) => {
    currentPaletteName = e.target.value;
    renderGrid();
    renderPreview();
    buildPalettePanel();
});

// ---------------------------------------------------------------------------
// Palette key panel
// ---------------------------------------------------------------------------
function buildPalettePanel() {
    const container = document.getElementById('palette-keys');
    container.innerHTML = '';

    const keys = getPaletteKeys();
    const palette = getPalette();

    // Transparent option first
    const transDiv = document.createElement('div');
    transDiv.className = 'palette-key' + (currentBrush === null ? ' active' : '');
    const transSwatch = document.createElement('div');
    transSwatch.className = 'palette-swatch transparent';
    transDiv.appendChild(transSwatch);
    const transLabel = document.createElement('span');
    transLabel.textContent = 'transparent';
    transDiv.appendChild(transLabel);
    transDiv.onclick = () => {
        currentBrush = null;
        buildPalettePanel();
    };
    container.appendChild(transDiv);

    for (const key of keys) {
        const div = document.createElement('div');
        div.className = 'palette-key' + (currentBrush === key ? ' active' : '');
        const swatch = document.createElement('div');
        swatch.className = 'palette-swatch';
        swatch.style.background = palette[key] || '#ff00ff';
        div.appendChild(swatch);
        const label = document.createElement('span');
        label.textContent = key;
        div.appendChild(label);
        div.onclick = () => {
            currentBrush = key;
            currentTool = 'paint';
            updateToolButtons();
            buildPalettePanel();
        };
        container.appendChild(div);
    }
}

// ---------------------------------------------------------------------------
// Pixel grid
// ---------------------------------------------------------------------------
function renderGrid() {
    const grid = document.getElementById('pixel-grid');
    grid.innerHTML = '';

    const pixels = getPixels();
    if (!pixels) return;

    const palette = getPalette();
    const h = pixels.length;
    const w = pixels[0] ? pixels[0].length : 0;

    // Ghost overlay data
    let ghostPixels = null;
    if (pinnedOverlay && !(pinnedOverlay.group === currentGroup && pinnedOverlay.key === currentKey)) {
        const pinned = sprites[pinnedOverlay.group]?.[pinnedOverlay.key];
        if (pinned) ghostPixels = pinned.pixels;
    }

    grid.style.gridTemplateColumns = `repeat(${w}, ${cellSize}px)`;
    grid.style.gridTemplateRows = `repeat(${h}, ${cellSize}px)`;
    grid.style.setProperty('--overlay-diff-color', `rgba(233, 160, 69, ${overlayOpacity})`);

    for (let y = 0; y < h; y++) {
        for (let x = 0; x < w; x++) {
            const cell = document.createElement('div');
            cell.className = 'pixel-cell';
            cell.style.width = cellSize + 'px';
            cell.style.height = cellSize + 'px';

            if (!showGrid) {
                cell.style.border = 'none';
            }

            const px = pixels[y][x];
            if (px === null) {
                cell.classList.add('transparent');
            } else {
                cell.style.background = palette[px] || '#ff00ff';
            }

            // Ghost overlay
            if (ghostPixels && y < ghostPixels.length && x < (ghostPixels[y]?.length || 0)) {
                const ghostPx = ghostPixels[y][x];
                const differs = ghostPx !== px;
                if (differs) cell.classList.add('overlay-diff');
                if (ghostPx !== null) {
                    const ghostColor = palette[ghostPx] || '#ff00ff';
                    if (px === null) {
                        // Current is transparent — show ghost clearly
                        const ghost = document.createElement('div');
                        ghost.className = 'overlay-ghost';
                        ghost.style.background = ghostColor;
                        ghost.style.opacity = overlayOpacity;
                        cell.appendChild(ghost);
                    } else if (differs) {
                        // Both have pixels but they differ — subtle tint
                        const ghost = document.createElement('div');
                        ghost.className = 'overlay-ghost';
                        ghost.style.background = ghostColor;
                        ghost.style.opacity = overlayOpacity * 0.55;
                        cell.appendChild(ghost);
                    }
                }
            }

            cell.dataset.x = x;
            cell.dataset.y = y;

            // Mouse events for painting
            cell.addEventListener('mousedown', onCellMouseDown);
            cell.addEventListener('mouseenter', onCellMouseEnter);
            cell.addEventListener('contextmenu', onCellRightClick);

            grid.appendChild(cell);
        }
    }

    document.getElementById('info-dims').textContent = `${w}×${h}px`;

    // Re-apply selection overlay after grid rebuild
    if (selection) renderSelectionOverlay();
}

function onCellMouseDown(e) {
    if (e.button === 2) return; // right-click handled separately
    e.preventDefault();
    const x = parseInt(e.target.dataset.x);
    const y = parseInt(e.target.dataset.y);

    if (currentTool === 'select') {
        isSelecting = true;
        selectionStart = { x, y };
        selection = { x1: x, y1: y, x2: x, y2: y };
        selectionBuffer = null;
        renderSelectionOverlay();
        return;
    }

    isPainting = true;
    lastPaintedCell = null;
    strokeStarted = false;
    applyTool(x, y);
}

function onCellMouseEnter(e) {
    const x = parseInt(e.target.dataset.x);
    const y = parseInt(e.target.dataset.y);
    const pixels = getPixels();

    // Selection drag
    if (isSelecting && selectionStart) {
        selection = {
            x1: Math.min(selectionStart.x, x),
            y1: Math.min(selectionStart.y, y),
            x2: Math.max(selectionStart.x, x),
            y2: Math.max(selectionStart.y, y),
        };
        renderSelectionOverlay();
    }

    // Update info bar
    if (pixels && y < pixels.length && x < pixels[y].length) {
        document.getElementById('info-pos').textContent = `(${x}, ${y})`;
        const currentPx = pixels[y][x] || 'transparent';
        const pinnedSpan = document.getElementById('info-pinned');
        if (pinnedOverlay && !(pinnedOverlay.group === currentGroup && pinnedOverlay.key === currentKey)) {
            const ghostPixels = sprites[pinnedOverlay.group]?.[pinnedOverlay.key]?.pixels;
            const ghostPx = ghostPixels?.[y]?.[x] ?? null;
            const ghostLabel = ghostPx || 'transparent';
            document.getElementById('info-key').textContent = `Current: ${currentPx}`;
            pinnedSpan.textContent = `Pinned: ${ghostLabel}`;
            pinnedSpan.style.display = '';
            pinnedSpan.style.color = ghostLabel !== currentPx ? '#e9a045' : '#777';
        } else {
            document.getElementById('info-key').textContent = currentPx;
            pinnedSpan.style.display = 'none';
        }
    }

    if (isPainting) {
        applyTool(x, y);
    }
}

function onCellRightClick(e) {
    e.preventDefault();
    // Eyedropper on right-click
    const x = parseInt(e.target.dataset.x);
    const y = parseInt(e.target.dataset.y);
    const pixels = getPixels();
    if (pixels) {
        currentBrush = pixels[y][x];
        currentTool = 'paint';
        updateToolButtons();
        buildPalettePanel();
    }
}

document.addEventListener('mouseup', () => { isPainting = false; lastPaintedCell = null; strokeStarted = false; isSelecting = false; });

// ---------------------------------------------------------------------------
// Tools
// ---------------------------------------------------------------------------
function applyTool(x, y) {
    const pixels = getPixels();
    if (!pixels || y >= pixels.length || x >= pixels[0].length) return;

    const cellId = `${x},${y}`;
    if (lastPaintedCell === cellId && currentTool !== 'pick') return;
    lastPaintedCell = cellId;

    if (currentTool === 'paint') {
        if (pixels[y][x] !== currentBrush) {
            if (!strokeStarted) { pushUndo(); strokeStarted = true; }
            pixels[y][x] = currentBrush;
            markDirty();
            renderGrid();
            renderPreview();
        }
    } else if (currentTool === 'erase') {
        if (pixels[y][x] !== null) {
            if (!strokeStarted) { pushUndo(); strokeStarted = true; }
            pixels[y][x] = null;
            markDirty();
            renderGrid();
            renderPreview();
        }
    } else if (currentTool === 'pick') {
        currentBrush = pixels[y][x];
        currentTool = 'paint';
        updateToolButtons();
        buildPalettePanel();
    } else if (currentTool === 'fill') {
        const target = pixels[y][x];
        if (target === currentBrush) return;
        pushUndo();
        floodFill(pixels, x, y, target, currentBrush);
        markDirty();
        renderGrid();
        renderPreview();
    }
}

function floodFill(pixels, startX, startY, target, replacement) {
    const h = pixels.length;
    const w = pixels[0].length;
    const stack = [[startX, startY]];
    while (stack.length > 0) {
        const [x, y] = stack.pop();
        if (x < 0 || x >= w || y < 0 || y >= h) continue;
        if (pixels[y][x] !== target) continue;
        pixels[y][x] = replacement;
        stack.push([x + 1, y], [x - 1, y], [x, y + 1], [x, y - 1]);
    }
}

// ---------------------------------------------------------------------------
// Undo / Redo
// ---------------------------------------------------------------------------
function pushUndo() {
    const id = spriteId(currentGroup, currentKey);
    if (!undoStacks[id]) undoStacks[id] = [];
    undoStacks[id].push(JSON.parse(JSON.stringify(getPixels())));
    // Clear redo on new action
    redoStacks[id] = [];
    // Limit stack size
    if (undoStacks[id].length > 100) undoStacks[id].shift();
}

function undo() {
    if (!currentGroup || !currentKey) return;
    const id = spriteId(currentGroup, currentKey);
    const stack = undoStacks[id];
    if (!stack || stack.length === 0) return;

    if (!redoStacks[id]) redoStacks[id] = [];
    redoStacks[id].push(JSON.parse(JSON.stringify(getPixels())));

    const prev = stack.pop();
    sprites[currentGroup][currentKey].pixels = prev;
    markDirty();
    renderGrid();
    renderPreview();
}

function redo() {
    if (!currentGroup || !currentKey) return;
    const id = spriteId(currentGroup, currentKey);
    const stack = redoStacks[id];
    if (!stack || stack.length === 0) return;

    if (!undoStacks[id]) undoStacks[id] = [];
    undoStacks[id].push(JSON.parse(JSON.stringify(getPixels())));

    const next = stack.pop();
    sprites[currentGroup][currentKey].pixels = next;
    markDirty();
    renderGrid();
    renderPreview();
}

function markDirty() {
    const id = spriteId(currentGroup, currentKey);
    dirtySprites.add(id);
    // Update the tree item
    document.querySelectorAll('.sprite-item').forEach(el => {
        const elId = spriteId(el.dataset.group, el.dataset.key);
        el.classList.toggle('dirty', dirtySprites.has(elId));
    });
    document.getElementById('info-dirty').textContent =
        dirtySprites.size > 0 ? `${dirtySprites.size} changed` : 'Clean';
}

// ---------------------------------------------------------------------------
// Half-block preview
// ---------------------------------------------------------------------------
function renderHalfBlockPreview(pixels, palette, canvas) {
    const h = pixels.length;
    const w = pixels[0] ? pixels[0].length : 0;

    canvas.width = w;
    canvas.height = h;
    canvas.style.width = (w * 4) + 'px';
    canvas.style.height = (h * 4) + 'px';

    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, w, h);

    for (let y = 0; y < h; y++) {
        for (let x = 0; x < w; x++) {
            const px = pixels[y] ? pixels[y][x] : null;
            if (px !== null) {
                ctx.fillStyle = palette[px] || '#ff00ff';
                ctx.fillRect(x, y, 1, 1);
            }
        }
    }
}

function renderPreview() {
    const bar = document.getElementById('preview-bar');
    bar.innerHTML = '';

    const pixels = getPixels();
    if (!pixels) return;

    if (currentGroup && (currentGroup.startsWith('facility') || currentGroup.startsWith('indicator'))) {
        // Single palette preview
        const palette = getPalette();
        const item = document.createElement('div');
        item.className = 'preview-item';
        const label = document.createElement('div');
        label.className = 'label';
        label.textContent = currentGroup.startsWith('indicator') ? currentKey : getFacilityType(currentKey);
        item.appendChild(label);
        const canvas = document.createElement('canvas');
        canvas.className = 'preview-canvas';
        renderHalfBlockPreview(pixels, palette, canvas);
        item.appendChild(canvas);
        bar.appendChild(item);
    } else {
        // Show all 4 pig palettes
        for (const [name, palette] of Object.entries(DATA.palettes.pig)) {
            const item = document.createElement('div');
            item.className = 'preview-item';
            const label = document.createElement('div');
            label.className = 'label';
            label.textContent = name;
            item.appendChild(label);
            const canvas = document.createElement('canvas');
            canvas.className = 'preview-canvas';
            renderHalfBlockPreview(pixels, palette, canvas);
            item.appendChild(canvas);
            bar.appendChild(item);
        }
    }
}

// ---------------------------------------------------------------------------
// Tool buttons
// ---------------------------------------------------------------------------
function updateToolButtons() {
    document.getElementById('tool-paint').classList.toggle('active-tool', currentTool === 'paint');
    document.getElementById('tool-erase').classList.toggle('active-tool', currentTool === 'erase');
    document.getElementById('tool-pick').classList.toggle('active-tool', currentTool === 'pick');
    document.getElementById('tool-fill').classList.toggle('active-tool', currentTool === 'fill');
    document.getElementById('tool-select').classList.toggle('active-tool', currentTool === 'select');
}

document.getElementById('tool-paint').onclick = () => { currentTool = 'paint'; updateToolButtons(); };
document.getElementById('tool-erase').onclick = () => { currentTool = 'erase'; updateToolButtons(); };
document.getElementById('tool-pick').onclick = () => { currentTool = 'pick'; updateToolButtons(); };
document.getElementById('tool-fill').onclick = () => { currentTool = 'fill'; updateToolButtons(); };
document.getElementById('tool-select').onclick = () => { currentTool = 'select'; updateToolButtons(); };
document.getElementById('btn-undo').onclick = undo;
document.getElementById('btn-redo').onclick = redo;

document.getElementById('btn-grid-toggle').onclick = () => {
    showGrid = !showGrid;
    renderGrid();
};

function togglePin() {
    if (!currentGroup || !currentKey) return;
    if (pinnedOverlay && pinnedOverlay.group === currentGroup && pinnedOverlay.key === currentKey) {
        // Same sprite — unpin
        pinnedOverlay = null;
    } else {
        // Pin current sprite (or replace existing pin)
        pinnedOverlay = { group: currentGroup, key: currentKey };
    }
    updatePinUI();
    renderGrid();
}

function updatePinUI() {
    const btn = document.getElementById('btn-pin');
    const info = document.getElementById('overlay-info');
    const opacitySlider = document.getElementById('overlay-opacity');
    const opacityLabel = document.getElementById('overlay-opacity-label');
    if (pinnedOverlay) {
        btn.textContent = 'Unpin';
        btn.classList.add('pin-active');
        info.textContent = 'Overlay: ' + pinnedOverlay.key;
        opacitySlider.style.display = '';
        opacityLabel.style.display = '';
    } else {
        btn.textContent = 'Pin';
        btn.classList.remove('pin-active');
        info.textContent = '';
        opacitySlider.style.display = 'none';
        opacityLabel.style.display = 'none';
    }
}

document.getElementById('btn-pin').onclick = togglePin;

document.getElementById('overlay-opacity').addEventListener('input', (e) => {
    overlayOpacity = parseInt(e.target.value) / 100;
    renderGrid();
});

document.getElementById('zoom-slider').addEventListener('input', (e) => {
    cellSize = parseInt(e.target.value);
    renderGrid();
});

// ---------------------------------------------------------------------------
// Selection overlay + shift
// ---------------------------------------------------------------------------
function renderSelectionOverlay() {
    // Toggle .selected class on cells inside the selection rect
    const grid = document.getElementById('pixel-grid');
    const cells = grid.querySelectorAll('.pixel-cell');
    cells.forEach(cell => {
        const cx = parseInt(cell.dataset.x);
        const cy = parseInt(cell.dataset.y);
        if (selection && cx >= selection.x1 && cx <= selection.x2 && cy >= selection.y1 && cy <= selection.y2) {
            cell.classList.add('selected');
        } else {
            cell.classList.remove('selected');
        }
    });
}

function shiftPixels(dx, dy) {
    const pixels = getPixels();
    if (!pixels) return;
    const h = pixels.length;
    const w = pixels[0].length;

    if (selection) {
        // The selectionBuffer is a floating copy of the content that travels
        // with the selection. It is the source of truth — pixels that move
        // off-grid are preserved in the buffer and reappear when moved back.
        const { x1, y1, x2, y2 } = selection;
        const selW = x2 - x1 + 1;
        const selH = y2 - y1 + 1;

        pushUndo();

        // First move: lift content into the buffer
        if (!selectionBuffer) {
            selectionBuffer = [];
            for (let sy = 0; sy < selH; sy++) {
                const row = [];
                for (let sx = 0; sx < selW; sx++) {
                    row.push(pixels[y1 + sy][x1 + sx]);
                }
                selectionBuffer.push(row);
            }
        }

        // Erase the buffer's current footprint from the grid
        for (let sy = 0; sy < selH; sy++) {
            for (let sx = 0; sx < selW; sx++) {
                const gy = y1 + sy, gx = x1 + sx;
                if (gy >= 0 && gy < h && gx >= 0 && gx < w) {
                    pixels[gy][gx] = null;
                }
            }
        }

        // Move selection coordinates (allowed to go out of bounds)
        selection.x1 += dx;
        selection.y1 += dy;
        selection.x2 += dx;
        selection.y2 += dy;

        // Stamp the buffer onto the grid at the new position
        const nx1 = selection.x1, ny1 = selection.y1;
        for (let sy = 0; sy < selH; sy++) {
            for (let sx = 0; sx < selW; sx++) {
                const gy = ny1 + sy, gx = nx1 + sx;
                if (gy >= 0 && gy < h && gx >= 0 && gx < w) {
                    pixels[gy][gx] = selectionBuffer[sy][sx];
                }
            }
        }
    } else {
        // Shift entire sprite
        pushUndo();
        const copy = pixels.map(row => [...row]);
        for (let y = 0; y < h; y++) {
            for (let x = 0; x < w; x++) {
                pixels[y][x] = null;
            }
        }
        for (let y = 0; y < h; y++) {
            for (let x = 0; x < w; x++) {
                const nx = x + dx;
                const ny = y + dy;
                if (nx >= 0 && nx < w && ny >= 0 && ny < h) {
                    pixels[ny][nx] = copy[y][x];
                }
            }
        }
    }

    markDirty();
    renderGrid();
    renderSelectionOverlay();
    renderPreview();
}

// ---------------------------------------------------------------------------
// Duplicate from source
// ---------------------------------------------------------------------------
function showDuplicateDropdown() {
    if (!currentGroup || !currentKey) return;
    const dropdown = document.getElementById('duplicate-dropdown');
    dropdown.innerHTML = '';

    const groupSprites = sprites[currentGroup];
    const keys = Object.keys(groupSprites).filter(k => k !== currentKey).sort();
    if (keys.length === 0) return;

    for (const key of keys) {
        const item = document.createElement('div');
        item.className = 'dup-item';
        item.textContent = key;
        item.onclick = () => {
            duplicateFrom(currentGroup, key);
            closeDuplicateDropdown();
        };
        dropdown.appendChild(item);
    }

    dropdown.classList.add('open');
    // Close on outside click (next tick so current click doesn't trigger it)
    setTimeout(() => document.addEventListener('click', closeDuplicateOnOutsideClick, { once: true }), 0);
}

function closeDuplicateDropdown() {
    document.getElementById('duplicate-dropdown').classList.remove('open');
}

function closeDuplicateOnOutsideClick(e) {
    const dropdown = document.getElementById('duplicate-dropdown');
    if (!dropdown.contains(e.target) && e.target.id !== 'btn-duplicate') {
        closeDuplicateDropdown();
    }
}

function duplicateFrom(group, sourceKey) {
    pushUndo();
    const source = sprites[group][sourceKey].pixels;
    sprites[currentGroup][currentKey].pixels = JSON.parse(JSON.stringify(source));
    markDirty();
    renderGrid();
    renderPreview();
}

document.getElementById('btn-duplicate').onclick = showDuplicateDropdown;

// ---------------------------------------------------------------------------
// Keyboard shortcuts
// ---------------------------------------------------------------------------
document.addEventListener('keydown', (e) => {
    if (e.ctrlKey || e.metaKey) {
        if (e.key === 'z' && !e.shiftKey) { e.preventDefault(); undo(); }
        if (e.key === 'z' && e.shiftKey) { e.preventDefault(); redo(); }
        if (e.key === 'y') { e.preventDefault(); redo(); }
        return;
    }
    if (e.key === 'p') { currentTool = 'paint'; updateToolButtons(); }
    if (e.key === 'e') { currentTool = 'erase'; updateToolButtons(); }
    if (e.key === 'i') { currentTool = 'pick'; updateToolButtons(); }
    if (e.key === 'g') { currentTool = 'fill'; updateToolButtons(); }
    if (e.key === 's') { currentTool = 'select'; updateToolButtons(); }
    if (e.key === 't') { togglePin(); }
    if (e.key === 'd') { showDuplicateDropdown(); }
    if (e.key === 'Escape') { selection = null; selectionStart = null; selectionBuffer = null; renderSelectionOverlay(); }
    // Arrow keys: shift pixels (only when select tool is active)
    if (currentTool === 'select' && ['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(e.key)) {
        e.preventDefault();
        const dx = e.key === 'ArrowLeft' ? -1 : e.key === 'ArrowRight' ? 1 : 0;
        const dy = e.key === 'ArrowUp' ? -1 : e.key === 'ArrowDown' ? 1 : 0;
        shiftPixels(dx, dy);
    }
});

// ---------------------------------------------------------------------------
// Export
// ---------------------------------------------------------------------------
document.getElementById('btn-export').onclick = async () => {
    const exportData = JSON.parse(JSON.stringify(DATA));
    exportData.sprites = JSON.parse(JSON.stringify(sprites));
    const json = JSON.stringify(exportData, null, 2);

    try {
        const resp = await fetch('/save', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: json,
        });
        if (resp.ok) {
            dirtySprites.clear();
            document.querySelectorAll('.sprite-item.dirty').forEach(el => el.classList.remove('dirty'));
            document.getElementById('info-dirty').textContent = 'Saved!';
        } else {
            document.getElementById('info-dirty').textContent = 'Save failed — check server';
        }
    } catch (e) {
        document.getElementById('info-dirty').textContent = 'Save failed — is the server running?';
    }
};

// ---------------------------------------------------------------------------
// Info
// ---------------------------------------------------------------------------
function updateInfo() {
    const pixels = getPixels();
    if (pixels) {
        const w = pixels[0] ? pixels[0].length : 0;
        const h = pixels.length;
        document.getElementById('info-dims').textContent = `${w}×${h}px`;
    }
    document.getElementById('info-dirty').textContent =
        dirtySprites.size > 0 ? `${dirtySprites.size} changed` : 'Clean';
}

// ---------------------------------------------------------------------------
// Init
// ---------------------------------------------------------------------------
function init() {
    buildSpriteTree();

    // Select first sprite
    const firstGroup = Object.keys(sprites).find(g => Object.keys(sprites[g]).length > 0);
    if (firstGroup) {
        const firstKey = Object.keys(sprites[firstGroup])[0];
        currentPaletteName = getAllPigPaletteNames()[0] || null;
        selectSprite(firstGroup, firstKey);

        // Default brush to first palette key
        const keys = getPaletteKeys();
        currentBrush = keys.length > 0 ? keys[0] : null;
        buildPalettePanel();
    }
}

init();
