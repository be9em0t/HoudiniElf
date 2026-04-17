const { invoke } = window.__TAURI__.core;

// --- Expanded mode elements ---
const folderInputEl = document.querySelector("#folder-input");
const loadFolderButton = document.querySelector("#load-folder");
const statusEl = document.querySelector("#status");
const tracksEl = document.querySelector("#tracks");
const trackTitleEl = document.querySelector("#track-title");
const trackMetaEl = document.querySelector("#track-meta");
const audioPlayer = document.querySelector("#audio-player");
const btnLoop = document.querySelector("#btn-loop");
const btnPrev = document.querySelector("#btn-prev");
const btnPlay = document.querySelector("#btn-play");
const btnNext = document.querySelector("#btn-next");
const btnCompact = document.querySelector("#btn-compact");
const btnClose = document.querySelector("#btn-close");
const btnTestSound = document.querySelector("#test-sound");
const debugEl = document.querySelector("#debug-log");

// --- Compact mode elements ---
const compactMode = document.querySelector("#compact-mode");
const expandedMode = document.querySelector("#expanded-mode");
const compactTrackTitle = document.querySelector("#compact-track-title");
const btnCompactExpand = document.querySelector("#btn-compact-expand");
const btnCompactClose = document.querySelector("#btn-compact-close");
const btnCompactLoop = document.querySelector("#btn-compact-loop");
const btnCompactPrev = document.querySelector("#btn-compact-prev");
const btnCompactPlay = document.querySelector("#btn-compact-play");
const btnCompactNext = document.querySelector("#btn-compact-next");
const btnCompactPlaylist = document.querySelector("#btn-compact-playlist");

let tracks = [];
let selectedIndex = -1;
let loopMode = false;
let currentUiMode = "expanded"; // "compact" | "expanded"
let appSettings = {
  lastOpenFolder: "",
  lastPlayedTrack: "",
  uiMode: "expanded",
};

function toFileUrl(filePath) {
  if (!filePath) return "";
  const normalized = filePath.replace(/\\/g, "/");
  const prefix = /^[A-Za-z]:/.test(normalized) ? "file:///" : "file://";
  const segments = normalized.split("/").map((segment) => encodeURIComponent(segment));
  return prefix + segments.join("/");
}

async function getAudioServerUrl(filePath) {
  const port = await invoke("local_audio_server_port");
  return `http://127.0.0.1:${port}/track?path=${encodeURIComponent(filePath)}`;
}

function setStatus(message, success = true) {
  statusEl.textContent = message;
  statusEl.classList.toggle("status-error", !success);
}

async function saveAppSettings(changes) {
  appSettings = { ...appSettings, ...changes };
  try {
    await invoke("save_settings", { settings: appSettings });
  } catch (error) {
    const message = typeof error === "string" ? error : error?.message || String(error);
    appendDebug(`save_settings failed: ${message}`);
  }
}

async function loadAppSettings() {
  try {
    const settings = await invoke("load_settings");
    appSettings = {
      lastOpenFolder: settings.lastOpenFolder || "",
      lastPlayedTrack: settings.lastPlayedTrack || "",
      uiMode: settings.uiMode || "expanded",
    };
    if (appSettings.uiMode) {
      setUiMode(appSettings.uiMode);
    }
    if (appSettings.lastOpenFolder) {
      folderInputEl.value = appSettings.lastOpenFolder;
      try {
        await loadFolder();
        if (appSettings.lastPlayedTrack) {
          const lastIndex = tracks.findIndex((track) => track.path === appSettings.lastPlayedTrack);
          if (lastIndex !== -1) {
            selectTrack(lastIndex);
          }
        }
      } catch (error) {
        appendDebug(`Restore settings failed: ${error?.message || String(error)}`);
      }
    }
  } catch (error) {
    appendDebug(`load_settings failed: ${error?.message || String(error)}`);
  }
}

function appendDebug(message) {
  const timestamp = new Date().toLocaleTimeString();
  debugEl.textContent = `[${timestamp}] ${message}`;
}

function testTone() {
  if (!window.AudioContext && !window.webkitAudioContext) {
    appendDebug("Web Audio API is not available.");
    setStatus("Web Audio API unavailable.", false);
    return;
  }

  const AudioContext = window.AudioContext || window.webkitAudioContext;
  const context = new AudioContext();
  const oscillator = context.createOscillator();
  const gain = context.createGain();

  oscillator.type = "sine";
  oscillator.frequency.value = 440;
  oscillator.connect(gain);
  gain.connect(context.destination);
  gain.gain.value = 0.1;

  oscillator.start();
  appendDebug("Playing test tone (440 Hz) for 1 second.");
  setStatus("Playing test tone.", true);

  setTimeout(() => {
    oscillator.stop();
    context.close();
    appendDebug("Test tone stopped.");
    setStatus("Test tone completed.", true);
  }, 1000);
}

// --- UI mode switching ---
function setUiMode(mode) {
  currentUiMode = mode;
  if (mode === "compact") {
    expandedMode.style.display = "none";
    compactMode.style.display = "flex";
    syncCompactState();
  } else {
    compactMode.style.display = "none";
    expandedMode.style.display = "block";
  }
  saveAppSettings({ uiMode: mode });
}

function syncCompactState() {
  const track = selectedIndex >= 0 ? tracks[selectedIndex] : null;
  compactTrackTitle.textContent = track ? track.name : "No track";
  // sync play/pause icon: codicon play = eb2c, pause = eb2d
  const isPlaying = audioPlayer.src && !audioPlayer.paused;
  btnCompactPlay.innerHTML = isPlaying ? "&#xeb2d;" : "&#xeb2c;";
  btnCompactPlay.classList.toggle("playing", isPlaying);
  btnCompactLoop.classList.toggle("active", loopMode);
}

function renderTracks() {
  tracksEl.innerHTML = "";
  if (tracks.length === 0) {
    tracksEl.innerHTML = "<li class=\"empty\">No audio tracks found.</li>";
    return;
  }

  tracks.forEach((track, index) => {
    const li = document.createElement("li");
    li.className = "track-item";
    if (index === selectedIndex) {
      li.classList.add("selected");
    }
    li.innerHTML = `
      <div class="track-row">
        <span class="track-name">${track.name}</span>
        <span class="track-ext">${track.extension.toUpperCase()}</span>
      </div>
      <div class="track-info">${(track.size / 1024 / 1024).toFixed(2)} MB</div>
    `;
    li.addEventListener("click", () => selectTrack(index));
    tracksEl.appendChild(li);
  });
}

async function selectTrack(index) {
  if (index < 0 || index >= tracks.length) {
    return;
  }
  selectedIndex = index;
  const track = tracks[index];
  trackTitleEl.textContent = track.name;
  trackMetaEl.textContent = `${track.extension.toUpperCase()} · ${(track.size / 1024 / 1024).toFixed(2)} MB`;
  syncCompactState();
  setStatus("Loading audio...");

  const fileUrl = toFileUrl(track.path);
  console.groupCollapsed("[audio] selectTrack");
  console.log("track.path:", track.path);
  console.log("audio.url:", fileUrl);
  console.groupEnd();

  try {
    const probe = await invoke("probe_local_audio_file", { path: track.path });
    appendDebug(`probe exists=${probe.exists}, is_file=${probe.is_file}, size=${probe.size}, sample=${probe.sample_hex}`);
  } catch (probeError) {
    const probeMessage = typeof probeError === "string" ? probeError : probeError?.message || String(probeError);
    console.error("probe_local_audio_file failed", probeError);
    appendDebug(`probe_local_audio_file failed: ${probeMessage}`);
  }

  try {
    const serverUrl = await getAudioServerUrl(track.path);
    audioPlayer.src = serverUrl;
    appendDebug(`audio src set to ${serverUrl}`);
    audioPlayer.load();
    await audioPlayer.play();
    btnPlay.textContent = "⏸";
    syncCompactState();
    setStatus("Playing.", true);
    saveAppSettings({ lastPlayedTrack: track.path });
  } catch (error) {
    const message = typeof error === "string" ? error : error?.message || "Unable to play audio.";
    console.error("play() failed", error);
    appendDebug(`play() failed: ${message}`);

    try {
      const base64Data = await invoke("read_local_audio_file", { path: track.path });
      const mime = `audio/${track.extension.toLowerCase()}`;
      const binary = Uint8Array.from(atob(base64Data), (c) => c.charCodeAt(0));
      const blob = new Blob([binary], { type: mime });
      const objectUrl = URL.createObjectURL(blob);
      audioPlayer.src = objectUrl;
      appendDebug(`audio blob url created: ${objectUrl}`);
      audioPlayer.load();
      await audioPlayer.play();
      btnPlay.textContent = "⏸";
      syncCompactState();
      setStatus("Playing from blob fallback.", true);
    } catch (fallbackError) {
      const fallbackMessage = typeof fallbackError === "string" ? fallbackError : fallbackError?.message || "Fallback playback failed.";
      console.error("blob fallback failed", fallbackError);
      appendDebug(`blob fallback failed: ${fallbackMessage}`);
      audioPlayer.removeAttribute("src");
      setStatus(fallbackMessage, false);
    }
  }

  renderTracks();
}

function selectNext() {
  if (tracks.length === 0) return;
  selectedIndex = (selectedIndex + 1) % tracks.length;
  selectTrack(selectedIndex);
}

function selectPrev() {
  if (tracks.length === 0) return;
  selectedIndex = (selectedIndex - 1 + tracks.length) % tracks.length;
  selectTrack(selectedIndex);
}

function toggleLoop() {
  loopMode = !loopMode;
  audioPlayer.loop = loopMode;
  btnLoop.classList.toggle("active", loopMode);
  btnCompactLoop.classList.toggle("active", loopMode);
}

function togglePlay() {
  if (!audioPlayer.src) {
    selectTrack(0);
    return;
  }
  if (audioPlayer.paused) {
    audioPlayer.play();
    btnPlay.textContent = "⏸";
  } else {
    audioPlayer.pause();
    btnPlay.textContent = "▶";
  }
  syncCompactState();
}

function clearSelection() {
  selectedIndex = -1;
  tracksEl.querySelectorAll("li").forEach((li) => li.classList.remove("selected"));
  audioPlayer.pause();
  audioPlayer.removeAttribute("src");
  trackTitleEl.textContent = "No track selected";
  trackMetaEl.textContent = "";
  btnPlay.textContent = "▶";
  syncCompactState();
  setStatus("Selection cleared.");
}

async function loadFolder() {
  const dir = folderInputEl.value.trim();
  if (!dir) {
    setStatus("Enter a folder path first.", false);
    return;
  }

  setStatus("Loading tracks...");
  try {
    const loadedTracks = await invoke("list_local_audio_files", { dir });
    tracks = loadedTracks;
    selectedIndex = -1;
    renderTracks();
    await saveAppSettings({ lastOpenFolder: dir });
    if (tracks.length > 0) {
      setStatus(`Loaded ${tracks.length} track(s). Click a track to play.`);
      appendDebug(`loaded ${tracks.length} track(s) from ${dir}`);
    } else {
      setStatus("No supported audio files found.", true);
      appendDebug(`no supported audio files found in ${dir}`);
    }
  } catch (error) {
    const message = typeof error === "string" ? error : error?.message || String(error);
    setStatus(message, false);
    appendDebug(`list_local_audio_files failed: ${message}`);
    tracks = [];
    renderTracks();
  }
}

window.addEventListener("DOMContentLoaded", () => {
  // --- Expanded mode bindings ---
  loadFolderButton.addEventListener("click", loadFolder);
  btnTestSound.addEventListener("click", testTone);
  btnLoop.addEventListener("click", toggleLoop);
  btnPrev.addEventListener("click", selectPrev);
  btnPlay.addEventListener("click", togglePlay);
  btnNext.addEventListener("click", selectNext);
  btnCompact.addEventListener("click", () => setUiMode("compact"));
  btnClose.addEventListener("click", clearSelection);

  // --- Compact mode bindings ---
  btnCompactExpand.addEventListener("click", () => setUiMode("expanded"));
  btnCompactClose.addEventListener("click", clearSelection);
  btnCompactLoop.addEventListener("click", toggleLoop);
  btnCompactPrev.addEventListener("click", selectPrev);
  btnCompactPlay.addEventListener("click", togglePlay);
  btnCompactNext.addEventListener("click", selectNext);
  btnCompactPlaylist.addEventListener("click", () => setUiMode("expanded"));

  audioPlayer.addEventListener("ended", () => {
    if (!loopMode) selectNext();
  });
  audioPlayer.addEventListener("loadstart", () => {
    console.log("audio loadstart", audioPlayer.src);
  });
  audioPlayer.addEventListener("loadedmetadata", () => {
    console.log("audio loadedmetadata", {
      duration: audioPlayer.duration,
      paused: audioPlayer.paused,
      readyState: audioPlayer.readyState,
    });
  });
  audioPlayer.addEventListener("canplay", () => {
    console.log("audio canplay", audioPlayer.readyState);
  });
  audioPlayer.addEventListener("canplaythrough", () => {
    console.log("audio canplaythrough", audioPlayer.readyState);
  });
  audioPlayer.addEventListener("error", () => {
    const error = audioPlayer.error;
    const message = error
      ? `Audio playback error ${error.code}: ${error.message || "unknown"}`
      : "Unknown audio playback error.";
    console.error(message, error);
    appendDebug(`audio error: ${message}`);
    setStatus(message, false);
  });
  audioPlayer.addEventListener("stalled", () => {
    console.log("Audio playback stalled (transient buffer event).");
    appendDebug("audio playback stalled (transient)");
  });
  renderTracks();
  loadAppSettings().catch(() => {});
});
