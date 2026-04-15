const { invoke } = window.__TAURI__.core;

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
const btnExpand = document.querySelector("#btn-expand");
const btnClose = document.querySelector("#btn-close");
const btnTestSound = document.querySelector("#test-sound");
const debugEl = document.querySelector("#debug-log");

let tracks = [];
let selectedIndex = -1;
let loopMode = false;

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
    setStatus("Playing.", true);
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
}

function clearSelection() {
  selectedIndex = -1;
  tracksEl.querySelectorAll("li").forEach((li) => li.classList.remove("selected"));
  audioPlayer.pause();
  audioPlayer.removeAttribute("src");
  trackTitleEl.textContent = "No track selected";
  trackMetaEl.textContent = "";
  btnPlay.textContent = "▶";
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
  loadFolderButton.addEventListener("click", loadFolder);
  btnTestSound.addEventListener("click", testTone);
  btnLoop.addEventListener("click", toggleLoop);
  btnPrev.addEventListener("click", selectPrev);
  btnPlay.addEventListener("click", togglePlay);
  btnNext.addEventListener("click", selectNext);
  btnExpand.addEventListener("click", () => setStatus("Expand is a placeholder.", true));
  btnClose.addEventListener("click", clearSelection);
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
});
