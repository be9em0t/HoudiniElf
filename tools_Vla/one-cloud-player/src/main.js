const { invoke } = window.__TAURI__.core;

const folderInputEl = document.querySelector("#folder-input");
const loadFolderButton = document.querySelector("#load-folder");
const statusEl = document.querySelector("#status");
const tracksEl = document.querySelector("#tracks");
const trackTitleEl = document.querySelector("#track-title");
const miniTrackTitleEl = document.querySelector("#mini-track-title");
const miniDragArea = document.querySelector("#mini-drag-area");
const trackMetaEl = document.querySelector("#track-meta");
const audioPlayer = document.querySelector("#audio-player");
const btnLoop = document.querySelector("#btn-loop");
const btnPrev = document.querySelector("#btn-prev");
const btnPlay = document.querySelector("#btn-play");
const btnNext = document.querySelector("#btn-next");
const btnExpand = document.querySelector("#btn-expand");
const btnClose = document.querySelector("#btn-close");
const btnTestSound = document.querySelector("#test-sound");
const debugEl = document.querySelector("#debug-log");
const modeExtendedButton = document.querySelector("#mode-extended");
const modeMiniButton = document.querySelector("#mode-mini");
const miniLoopButton = document.querySelector("#mini-loop");
const miniPrevButton = document.querySelector("#mini-prev");
const miniPlayButton = document.querySelector("#mini-play");
const miniPlayIcon = document.querySelector("#mini-play-icon");
const miniNextButton = document.querySelector("#mini-next");
const miniPlaylistButton = document.querySelector("#mini-playlist");
const miniExpandButton = document.querySelector("#mini-expand");
const miniCloseButton = document.querySelector("#mini-close");

const PLAY_ICON = "";
const PAUSE_ICON = "";
const UI_MODE_EXTENDED = "extended";
const UI_MODE_MINI = "mini";

let tracks = [];
let selectedIndex = -1;
let loopMode = false;
let appSettings = {
  lastOpenFolder: "",
  lastPlayedTrack: "",
  uiMode: UI_MODE_EXTENDED,
};

function setStatus(message, success = true) {
  statusEl.textContent = message;
  statusEl.classList.toggle("status-error", !success);
}

function getCurrentWindow() {
  try {
    return window.__TAURI__?.window?.getCurrentWindow?.() || null;
  } catch {
    return null;
  }
}

async function startMiniWindowDrag(event) {
  if (event.button !== 0) {
    return;
  }

  const currentWindow = getCurrentWindow();
  if (!currentWindow?.startDragging) {
    return;
  }

  try {
    await currentWindow.startDragging();
  } catch (error) {
    appendDebug(`Window drag skipped: ${error?.message || String(error)}`);
  }
}

function setTrackLabels(track) {
  const title = track?.name || "No track selected";
  trackTitleEl.textContent = title;
  miniTrackTitleEl.textContent = title;
  trackMetaEl.textContent = track
    ? `${track.extension.toUpperCase()} · ${(track.size / 1024 / 1024).toFixed(2)} MB`
    : "";
}

function updatePlayButtons() {
  const isPlaying = Boolean(audioPlayer.src && !audioPlayer.paused);
  btnPlay.innerHTML = isPlaying ? PAUSE_ICON : PLAY_ICON;
  miniPlayIcon.textContent = isPlaying ? PAUSE_ICON : PLAY_ICON;
  miniPlayButton.classList.toggle("is-playing", isPlaying);
}

function updateLoopButtons() {
  btnLoop.classList.toggle("active", loopMode);
  miniLoopButton.classList.toggle("active", loopMode);
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

function appendDebug(message) {
  const timestamp = new Date().toLocaleTimeString();
  debugEl.textContent = `[${timestamp}] ${message}`;
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

async function applyWindowPreset(mode) {
  try {
    await invoke("set_ui_window_mode", { mode });
  } catch (error) {
    const currentWindow = getCurrentWindow();
    if (!currentWindow) {
      appendDebug(`Window resize skipped: ${error?.message || String(error)}`);
      return;
    }

    try {
      if (mode === UI_MODE_MINI) {
        await currentWindow.setSize(new window.__TAURI__.dpi.LogicalSize(250, 107));
        await currentWindow.setResizable(false);
      } else {
        await currentWindow.setResizable(true);
        await currentWindow.setSize(new window.__TAURI__.dpi.LogicalSize(960, 760));
      }
    } catch (fallbackError) {
      appendDebug(`Window resize skipped: ${fallbackError?.message || String(fallbackError)}`);
    }
  }
}

async function setUiMode(mode, persist = true) {
  const safeMode = mode === UI_MODE_MINI ? UI_MODE_MINI : UI_MODE_EXTENDED;
  appSettings.uiMode = safeMode;
  document.body.dataset.uiMode = safeMode;
  modeExtendedButton.classList.toggle("is-active", safeMode === UI_MODE_EXTENDED);
  modeMiniButton.classList.toggle("is-active", safeMode === UI_MODE_MINI);
  await applyWindowPreset(safeMode);
  if (persist) {
    await saveAppSettings({ uiMode: safeMode });
  }
}

async function closeWindow() {
  const currentWindow = getCurrentWindow();
  if (currentWindow?.close) {
    await currentWindow.close();
    return;
  }

  clearSelection();
  setStatus("Window API unavailable, selection cleared instead.", false);
}

async function exitApplication() {
  try {
    await invoke("exit_application");
  } catch (error) {
    appendDebug(`App exit failed: ${error?.message || String(error)}`);
    await closeWindow();
  }
}

async function loadAppSettings() {
  try {
    const settings = await invoke("load_settings");
    appSettings = {
      lastOpenFolder: settings.lastOpenFolder || "",
      lastPlayedTrack: settings.lastPlayedTrack || "",
      uiMode: settings.uiMode === UI_MODE_MINI ? UI_MODE_MINI : UI_MODE_EXTENDED,
    };

    await setUiMode(appSettings.uiMode, false);

    if (appSettings.lastOpenFolder) {
      folderInputEl.value = appSettings.lastOpenFolder;
      try {
        await loadFolder(false);
        if (appSettings.lastPlayedTrack) {
          const lastIndex = tracks.findIndex((track) => track.path === appSettings.lastPlayedTrack);
          if (lastIndex !== -1) {
            await selectTrack(lastIndex);
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

async function getAudioServerUrl(filePath) {
  const port = await invoke("local_audio_server_port");
  return `http://127.0.0.1:${port}/track?path=${encodeURIComponent(filePath)}`;
}

async function selectTrack(index) {
  if (index < 0 || index >= tracks.length) {
    return;
  }

  selectedIndex = index;
  const track = tracks[index];
  setTrackLabels(track);
  setStatus("Loading audio...");

  try {
    const probe = await invoke("probe_local_audio_file", { path: track.path });
    appendDebug(`probe exists=${probe.exists}, is_file=${probe.is_file}, size=${probe.size}, sample=${probe.sample_hex}`);
  } catch (probeError) {
    const probeMessage = typeof probeError === "string" ? probeError : probeError?.message || String(probeError);
    appendDebug(`probe_local_audio_file failed: ${probeMessage}`);
  }

  try {
    const serverUrl = await getAudioServerUrl(track.path);
    audioPlayer.src = serverUrl;
    appendDebug(`audio src set to ${serverUrl}`);
    audioPlayer.load();
    await audioPlayer.play();
    updatePlayButtons();
    setStatus("Playing.", true);
    await saveAppSettings({ lastPlayedTrack: track.path });
  } catch (error) {
    const message = typeof error === "string" ? error : error?.message || "Unable to play audio.";
    appendDebug(`play() failed: ${message}`);

    try {
      const base64Data = await invoke("read_local_audio_file", { path: track.path });
      const mime = `audio/${track.extension.toLowerCase()}`;
      const binary = Uint8Array.from(atob(base64Data), (char) => char.charCodeAt(0));
      const blob = new Blob([binary], { type: mime });
      const objectUrl = URL.createObjectURL(blob);
      audioPlayer.src = objectUrl;
      appendDebug(`audio blob url created: ${objectUrl}`);
      audioPlayer.load();
      await audioPlayer.play();
      updatePlayButtons();
      setStatus("Playing from blob fallback.", true);
    } catch (fallbackError) {
      const fallbackMessage = typeof fallbackError === "string"
        ? fallbackError
        : fallbackError?.message || "Fallback playback failed.";
      appendDebug(`blob fallback failed: ${fallbackMessage}`);
      audioPlayer.removeAttribute("src");
      updatePlayButtons();
      setStatus(fallbackMessage, false);
    }
  }

  renderTracks();
}

async function selectNext() {
  if (tracks.length === 0) return;
  const nextIndex = (selectedIndex + 1 + tracks.length) % tracks.length;
  await selectTrack(nextIndex);
}

async function selectPrev() {
  if (tracks.length === 0) return;
  const prevIndex = (selectedIndex - 1 + tracks.length) % tracks.length;
  await selectTrack(prevIndex);
}

function toggleLoop() {
  loopMode = !loopMode;
  audioPlayer.loop = loopMode;
  updateLoopButtons();
}

async function togglePlay() {
  if (!audioPlayer.src) {
    if (tracks.length > 0) {
      await selectTrack(selectedIndex >= 0 ? selectedIndex : 0);
    } else {
      setStatus("Load a folder with audio first.", false);
    }
    return;
  }

  if (audioPlayer.paused) {
    await audioPlayer.play();
  } else {
    audioPlayer.pause();
  }
  updatePlayButtons();
}

function clearSelection() {
  selectedIndex = -1;
  audioPlayer.pause();
  audioPlayer.removeAttribute("src");
  setTrackLabels(null);
  updatePlayButtons();
  setStatus("Selection cleared.");
  renderTracks();
}

async function loadFolder(persist = true) {
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
    setTrackLabels(null);
    updatePlayButtons();
    if (persist) {
      await saveAppSettings({ lastOpenFolder: dir });
    }

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
    setTrackLabels(null);
  }
}

window.addEventListener("DOMContentLoaded", () => {
  document.body.dataset.uiMode = UI_MODE_EXTENDED;
  setTrackLabels(null);
  updatePlayButtons();
  updateLoopButtons();

  loadFolderButton.addEventListener("click", () => loadFolder());
  btnTestSound.addEventListener("click", testTone);

  btnLoop.addEventListener("click", toggleLoop);
  miniLoopButton.addEventListener("click", toggleLoop);

  btnPrev.addEventListener("click", () => selectPrev());
  miniPrevButton.addEventListener("click", () => selectPrev());

  btnPlay.addEventListener("click", () => togglePlay());
  miniPlayButton.addEventListener("click", () => togglePlay());

  btnNext.addEventListener("click", () => selectNext());
  miniNextButton.addEventListener("click", () => selectNext());

  modeExtendedButton.addEventListener("click", () => setUiMode(UI_MODE_EXTENDED));
  modeMiniButton.addEventListener("click", () => setUiMode(UI_MODE_MINI));
  btnExpand.addEventListener("click", () => setUiMode(UI_MODE_MINI));
  miniExpandButton.addEventListener("click", () => setUiMode(UI_MODE_EXTENDED));
  miniPlaylistButton.addEventListener("click", () => setUiMode(UI_MODE_EXTENDED));

  btnClose.addEventListener("click", () => closeWindow());
  miniCloseButton.addEventListener("click", () => exitApplication());
  miniDragArea.addEventListener("mousedown", (event) => {
    startMiniWindowDrag(event).catch(() => {});
  });

  audioPlayer.addEventListener("ended", () => {
    if (!loopMode) {
      selectNext().catch(() => {});
    }
  });
  audioPlayer.addEventListener("play", updatePlayButtons);
  audioPlayer.addEventListener("pause", updatePlayButtons);
  audioPlayer.addEventListener("loadstart", () => {
    appendDebug(`audio loadstart ${audioPlayer.src}`);
  });
  audioPlayer.addEventListener("error", () => {
    const error = audioPlayer.error;
    const message = error
      ? `Audio playback error ${error.code}: ${error.message || "unknown"}`
      : "Unknown audio playback error.";
    appendDebug(`audio error: ${message}`);
    setStatus(message, false);
    updatePlayButtons();
  });
  audioPlayer.addEventListener("stalled", () => {
    appendDebug("audio playback stalled (transient)");
  });

  renderTracks();
  loadAppSettings().catch(() => {});
});
