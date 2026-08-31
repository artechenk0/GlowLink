const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
let syncing = false;
let booting = true;
let powerOn = true;
let powerBusy = false;
const COLOR_STORAGE_KEY = "ledsetup-current-color";
const RECENT_COLORS_STORAGE_KEY = "ledsetup-recent-colors";
const DEFAULT_COLOR = { r: 255, g: 85, b: 77, name: "Красный" };
const storedColor = loadStoredColor();
let currentColor = storedColor ?? DEFAULT_COLOR;
const BLUETOOTH_ICON = '<svg class="bluetooth-icon" viewBox="0 0 24 24" aria-hidden="true"><path d="m7 7 10 10-5 5V2l5 5L7 17m0 0 10-10"/></svg>';

// Keep the last selected color visible even before pywebview finishes booting.
setColor(currentColor.r, currentColor.g, currentColor.b, currentColor.name);

function api() { return window.pywebview.api; }
function hex(r, g, b) { return `#${[r, g, b].map((v) => v.toString(16).padStart(2, "0")).join("")}`.toUpperCase(); }
function luminance(r, g, b) { return (r * 299 + g * 587 + b * 114) / 1000; }
function validColor(value) {
  return value && [value.r, value.g, value.b].every((channel) => Number.isInteger(channel) && channel >= 0 && channel <= 255);
}
function loadStoredColor() {
  try {
    const color = JSON.parse(localStorage.getItem(COLOR_STORAGE_KEY));
    return validColor(color) ? color : null;
  } catch (_) { return null; }
}
function loadRecentColors() {
  try {
    const colors = JSON.parse(localStorage.getItem(RECENT_COLORS_STORAGE_KEY));
    return Array.isArray(colors) ? colors.filter(validColor).slice(0, 4) : [];
  } catch (_) { return []; }
}
function saveColor(color, remember) {
  try {
    localStorage.setItem(COLOR_STORAGE_KEY, JSON.stringify(color));
    if (!remember) return;
    const colors = loadRecentColors().filter((item) => hex(item.r, item.g, item.b) !== hex(color.r, color.g, color.b));
    localStorage.setItem(RECENT_COLORS_STORAGE_KEY, JSON.stringify([color, ...colors].slice(0, 4)));
  } catch (_) { /* The app remains usable when browser storage is unavailable. */ }
}
function status(element, text, kind = "") {
  element.textContent = text || "";
  element.className = `status ${kind}`;
  element.hidden = !text;
}
function toast(text) { const el = $("#toast"); el.textContent = text; el.hidden = false; setTimeout(() => { el.hidden = true; }, 2200); }
function setControlsEnabled(enabled) {
  const colorControls = $$("#color-panel .preset, #custom-color, #power");
  colorControls.forEach((control) => { control.disabled = !enabled || syncing; });
  $("#sync").disabled = !enabled;
  setMonitorEnabled(enabled && !syncing);
  $("#control-view").setAttribute("aria-busy", String(!enabled));
}
function setBooting(on) {
  booting = on;
  $("#boot-layer").hidden = !on;
  $(".app").classList.toggle("booting", on);
  setControlsEnabled(!on && Boolean(window.__ledConnected));
}
function setPowerState(on) {
  powerOn = on;
  const button = $("#power");
  button.classList.toggle("off", !on);
  $("#power span").textContent = on ? "Включено" : "Выключено";
}
function setPowerBusy(on) {
  powerBusy = on;
  $("#power").disabled = on || booting || !window.__ledConnected;
}
function setColor(r, g, b, name = "Свой цвет", send = false, remember = false) {
  if (![r, g, b].every((value) => Number.isInteger(value) && value >= 0 && value <= 255)) return;
  currentColor = { r, g, b, name };
  saveColor(currentColor, remember);
  const value = hex(r, g, b);
  const preview = $("#color-preview");
  preview.style.background = value;
  preview.style.color = luminance(r, g, b) > 160 ? "#170d0d" : "#fff";
  $("#color-name").textContent = name;
  $("#color-code").textContent = value;
  $$(".preset").forEach((item) => item.classList.toggle("active", item.dataset.color === value));
  if (send && !syncing) api().set_color(r, g, b);
}
function showView(name) { $("#control-view").hidden = name !== "control"; $("#device-view").hidden = name !== "device"; $("#menu-wrap").hidden = name !== "control"; }
function refreshState(state) {
  if (!state) return;
  const dot = $("#link-dot");
  window.__ledConnected = Boolean(state.connected);
  setControlsEnabled(!booting && window.__ledConnected);
  if (!state.device) { $("#device-label").textContent = "лента не выбрана"; $("#link-label").textContent = "Нет устройства"; dot.className = "dot offline"; $("#connection-toggle").textContent = "Подключить"; return; }
  $("#device-label").textContent = `${state.device.name || "без имени"} · ${state.device.address}`;
  $("#link-label").textContent = state.connected ? "Лента подключена" : "Лента не подключена";
  dot.className = state.connected ? "dot" : "dot offline";
  $("#connection-toggle").textContent = state.connected ? "Отключить" : "Подключить";
}
function escapeHtml(value) { return String(value).replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;"); }
function renderDevices(hits) {
  const root = $("#device-list"); root.replaceChildren(); root.hidden = !hits.length;
  hits.forEach((hit) => {
    const card = document.createElement("button"); card.type = "button"; card.className = "device-card";
    card.innerHTML = `<span class="device-mark">${BLUETOOTH_ICON}</span><span><strong>${escapeHtml(hit.name || "Неизвестное устройство")}</strong><small>${escapeHtml(hit.address)}</small></span>${hit.lednetwf ? '<span class="badge">Рекомендуем</span>' : `<span class="signal">${hit.rssi ?? ""} dBm</span>`}`;
    card.onclick = () => { status($("#color-status"), "Подключаемся…", "busy"); api().select_device(hit.address); };
    root.appendChild(card);
  });
}
function openModal(name) {
  const sheet = $("#sheet"); sheet.replaceChildren($(`#${name}-template`).content.cloneNode(true)); $("#overlay").hidden = false; $("#menu").hidden = true;
  $$(".close", sheet).forEach((button) => button.onclick = () => { $("#overlay").hidden = true; });
  if (name === "settings") loadSettings();
  if (name === "forget") $("[data-action=forget]", sheet).onclick = () => api().forget_device();
  if (name === "color") bindColorModal();
}
async function loadSettings() { const settings = await api().get_settings(); $("#set-scan").value = settings.scan_timeout; $("#set-conn").value = settings.connect_timeout; $("[data-action=save]").onclick = async () => { const result = await api().save_settings($("#set-scan").value, $("#set-conn").value, false); if (result.kind === "ok") { $("#overlay").hidden = true; toast("Настройки сохранены"); } else { status($("#set-status"), result.text, result.kind); } }; }
function bindColorModal() {
  const area = $("#picker-area"), cursor = $("#picker-cursor"), hue = $("#hue"), rgb = $$(".rgb"), input = $("#hex");
  let saturation = 0, value = 1;
  const clamp = (number) => Math.max(0, Math.min(255, Math.round(Number(number) || 0)));
  const hsvToRgb = (h, s, v) => {
    const c = v * s;
    const x = c * (1 - Math.abs((h / 60) % 2 - 1));
    const m = v - c;
    const channels = h < 60 ? [c, x, 0] : h < 120 ? [x, c, 0] : h < 180 ? [0, c, x] : h < 240 ? [0, x, c] : h < 300 ? [x, 0, c] : [c, 0, x];
    return channels.map((channel) => Math.round((channel + m) * 255));
  };
  const rgbToHsv = (r, g, b) => {
    const [red, green, blue] = [r, g, b].map((channel) => clamp(channel) / 255);
    const max = Math.max(red, green, blue), min = Math.min(red, green, blue), delta = max - min;
    let h = 0;
    if (delta && max === red) h = 60 * (((green - blue) / delta) % 6);
    else if (delta && max === green) h = 60 * ((blue - red) / delta + 2);
    else if (delta) h = 60 * ((red - green) / delta + 4);
    return [(h + 360) % 360, max ? delta / max : 0, max];
  };
  const paint = () => {
    area.style.setProperty("--picker-hue", hue.value);
    cursor.style.left = `${saturation * 100}%`;
    cursor.style.top = `${(1 - value) * 100}%`;
  };
  const applyHsv = () => {
    const channels = hsvToRgb(Number(hue.value), saturation, value);
    channels.forEach((channel, index) => { rgb[index].value = channel; });
    input.value = hex(...channels);
    paint();
  };
  const applyRgb = (channels) => {
    const values = channels.map(clamp);
    values.forEach((channel, index) => { rgb[index].value = channel; });
    const [selectedHue, selectedSaturation, selectedValue] = rgbToHsv(...values);
    hue.value = Math.round(selectedHue);
    saturation = selectedSaturation;
    value = selectedValue;
    input.value = hex(...values);
    paint();
  };
  const pickAt = (event) => {
    const rect = area.getBoundingClientRect();
    saturation = Math.max(0, Math.min(1, (event.clientX - rect.left) / rect.width));
    value = 1 - Math.max(0, Math.min(1, (event.clientY - rect.top) / rect.height));
    applyHsv();
  };
  area.onpointerdown = (event) => { area.setPointerCapture(event.pointerId); pickAt(event); };
  area.onpointermove = (event) => { if (area.hasPointerCapture(event.pointerId)) pickAt(event); };
  hue.oninput = applyHsv;
  rgb.forEach((item) => item.oninput = () => applyRgb(rgb.map((field) => field.value)));
  input.oninput = () => {
    if (!/^#[0-9a-f]{6}$/i.test(input.value)) return;
    applyRgb([1, 3, 5].map((index) => parseInt(input.value.slice(index, index + 2), 16)));
  };
  const recent = $("#recent-colors");
  const recentList = $("#recent-colors-list");
  const colors = loadRecentColors();
  recent.hidden = !colors.length;
  colors.forEach((color) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "recent-color";
    button.style.background = hex(color.r, color.g, color.b);
    button.title = hex(color.r, color.g, color.b);
    button.setAttribute("aria-label", `Выбрать ${button.title}`);
    button.onclick = () => applyRgb([color.r, color.g, color.b]);
    recentList.appendChild(button);
  });
  $("[data-action=apply]").onclick = () => {
    const values = rgb.map((field) => clamp(field.value));
    setColor(...values, "Свой цвет", true, true);
    $("#overlay").hidden = true;
    toast("Цвет применён");
  };
  applyRgb([currentColor.r, currentColor.g, currentColor.b]);
}
function setMonitorEnabled(enabled) { const trigger = $("#monitor-trigger"); const options = $("#monitor-options"); trigger.disabled = !enabled; trigger.setAttribute("aria-expanded", String(enabled && !options.hidden)); if (!enabled) { options.hidden = true; $("#monitor-select").classList.remove("open"); } }
function setSyncing(on, text, kind) { syncing = on; $("#sync").classList.toggle("off", on); $("#sync span").textContent = on ? "Остановить синхронизацию" : "Начать синхронизацию"; setMonitorEnabled(!on && !booting && Boolean(window.__ledConnected)); $("#sync-hint").textContent = text || "Во время синхронизации ручной выбор цвета будет недоступен."; if (text) status($("#color-status"), text, kind); }
async function loadMonitors() { const data = await api().list_monitors(); const options = $("#monitor-options"); options.replaceChildren(); const monitors = data.monitors || []; const selected = monitors.find((monitor) => monitor.id === data.selected_id) || monitors[0]; monitors.forEach((monitor) => { const option = document.createElement("button"); option.type = "button"; option.className = "select-option"; option.dataset.value = monitor.id; option.textContent = monitor.label; option.setAttribute("aria-selected", String(selected?.id === monitor.id)); option.onclick = () => { if (syncing || booting || !window.__ledConnected) return; $("#monitor-value").textContent = monitor.label; options.hidden = true; $("#monitor-select").classList.remove("open"); $("#monitor-trigger").setAttribute("aria-expanded", "false"); $$(".select-option", options).forEach((item) => item.setAttribute("aria-selected", String(item === option))); api().select_monitor(monitor.id); }; options.appendChild(option); }); $("#monitor-value").textContent = selected?.label || "Мониторы не найдены"; }
window.__led = {
  onScan(result) { $("#scan").disabled = false; $("#scan").textContent = "Найти ленту"; renderDevices(result.hits || []); const state = $("#scan-state"); state.innerHTML = result.kind === "err" ? `<div class="status">${escapeHtml(result.text)}</div>` : `<div class="status good">✓ ${escapeHtml(result.text || "Выберите найденную ленту")}</div>`; $("#scan-again").hidden = false; },
  onSelected(message) { showView("control"); refreshState(message.state); setColor(currentColor.r, currentColor.g, currentColor.b, currentColor.name, true); status($("#color-status"), ""); },
  onMsg(message) {
    refreshState(message.state);
    if (powerBusy && message.kind === "err") { setPowerState(powerOn); setPowerBusy(false); }
    if (powerBusy && message.text?.startsWith("Лента выключена")) { setPowerState(false); setPowerBusy(false); }
    if (powerBusy && message.text?.startsWith("Включение (гипотеза)")) { setPowerState(true); setPowerBusy(false); }
    if (message.text?.startsWith("Подключено")) {
      setBooting(false);
      setColor(currentColor.r, currentColor.g, currentColor.b, currentColor.name, true);
      status($("#color-status"), "");
      return;
    }
    if (message.text?.startsWith("Включение (гипотеза)")) return;
    if (message.text?.includes("GATT ")) {
      toast("Техническая диагностика скрыта из основного окна");
      return;
    }
    if (message.kind === "err") setBooting(false);
    status($("#color-status"), message.text, message.kind);
  },
  onGatt(message) { if (message.kind === "err") status($("#color-status"), message.text, "err"); },
  onForgot(message) { $("#overlay").hidden = true; showView("device"); status($("#scan-state"), message.text, message.kind); },
  onSync(event) { setSyncing(event.running, event.text, event.kind); if ([event.r, event.g, event.b].every((channel) => Number.isInteger(channel))) { $("#screen-preview").style.background = hex(event.r, event.g, event.b); $("#screen-code").textContent = hex(event.r, event.g, event.b); } refreshState(event.state); },
};
window.addEventListener("pywebviewready", async () => {
  $$("[data-tab]").forEach((tab) => tab.onclick = () => { const screen = tab.dataset.tab === "screen"; $$(".tab").forEach((item) => item.classList.toggle("active", item === tab)); $("#tab-indicator").classList.toggle("screen", screen); $("#color-panel").hidden = screen; $("#screen-panel").hidden = !screen; if (screen) loadMonitors(); });
  $$(".preset").forEach((button) => button.onclick = () => { const value = button.dataset.color.slice(1).match(/../g).map((item) => parseInt(item, 16)); setColor(...value, button.dataset.name, true, true); });
  $("#power").onclick = () => { if (powerBusy || booting || !window.__ledConnected) return; const next = !powerOn; setPowerBusy(true); $("#power span").textContent = next ? "Включение…" : "Выключение…"; const request = next ? api().power_on() : api().power_off(); Promise.resolve(request).catch(() => { setPowerState(powerOn); setPowerBusy(false); status($("#color-status"), "Не удалось отправить команду питания.", "err"); }); };
  $("#sync").onclick = () => syncing ? api().stop_sync() : api().start_sync();
  $("#connection-toggle").onclick = () => api().toggle_connection();
  $("#more").onclick = () => { const menu = $("#menu"); menu.hidden = !menu.hidden; $("#more").setAttribute("aria-expanded", String(!menu.hidden)); };
  $$('[data-modal]').forEach((button) => button.onclick = () => openModal(button.dataset.modal));
  $("#custom-color").onclick = () => openModal("color");
  $("#change-device").onclick = () => { if (syncing) api().stop_sync(); showView("device"); };
  $("#device-back").onclick = () => showView("control");
  $("#scan").onclick = $("#scan-again").onclick = () => { $("#scan").disabled = true; $("#scan").textContent = "Ищем…"; status($("#scan-state"), "Ищем устройства рядом…", "busy"); api().scan(); };
  $("#monitor-trigger").onclick = () => { if (syncing || booting || !window.__ledConnected) return; const options = $("#monitor-options"); options.hidden = !options.hidden; $("#monitor-select").classList.toggle("open", !options.hidden); $("#monitor-trigger").setAttribute("aria-expanded", String(!options.hidden)); };
  $("#overlay").onclick = (event) => { if (event.target.id === "overlay") $("#overlay").hidden = true; }; document.addEventListener("keydown", (event) => { if (event.key === "Escape") $("#overlay").hidden = true; });
  const state = await api().get_state();
  if (!storedColor && Array.isArray(state.color) && state.color.length === 3) setColor(...state.color, "Свой цвет");
  refreshState(state);
  showView(state.device ? "control" : "device");
  if (state.device && state.auto_connect) { status($("#color-status"), "Подключаемся…", "busy"); api().connect(); } else setBooting(false);
});
