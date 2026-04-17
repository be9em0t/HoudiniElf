One Cloud Player - MVP Design Document

Overview
--------
One Cloud Player is a cross-platform desktop music player that streams audio from a specified OneDrive folder. The MVP will focus on a Rust + Tauri implementation, providing a native desktop app with a web-based UI and a local caching/download engine.

Goals
-----
- Play audio files stored in a configured OneDrive folder.
- Start playback quickly using progressive download / streaming.
- Cache downloaded audio locally to reduce repeated downloads.
- Support both macOS and Windows for the MVP.
- Keep the architecture modular for future mobile or service-based expansion.

MVP1 Local Scope
---------
- [x] Recreate simple mini-player HTML+CSS prototype
- [x] Initialize Tauri workspace and project structure
- [x] Install Rust toolchain
- [x] Run npm install for project dependencies
- [x] Build Rust backend skeleton and command API
- [x] Add local audio file listing and simple player shell
- [x] Play individual audio files
- [x] Fix local HTTP audio server transient stalled handling and user-facing playback status
- [x] Settings storage (last open folder, last played track)
- [x] Window UI: track name, expand (placeholder), close
- [ ] Player UI controls: loop (placeholder), previous, play/pause, next, track selection.
- [x] Compact/expanded mode switching with settings persistence

Settings storage strategy
---------
- Store all local app state under one single root directory where possible, instead of scattering files across multiple OS locations.
- Use a portable mode preference: if the app can write next to its executable/root folder, keep `settings.json`, `cache/`, `auth/`, and any local files together there.
- If portable root is unavailable, fall back to a single platform-specific app directory, still keeping data contained in one app-specific folder.
- Store app settings in `settings.json` as a small JSON object containing last open folder, last played track, window position/size, and selected library.
- Keep all metadata and cache under this same root directory so the app remains predictable and easy to move.

MVP2 Connected Scope
---------
- OneDrive authentication and folder selection.
- Improve robust streaming with ranged downloads and resilient local audio serving.
- List audio files from a specified OneDrive folder.
- Stream individual audio files using ranged downloads.
- Local cache of downloaded data with a simple cache policy.
- UI controls: play, pause, seek, and track selection.
- Playback should start before the entire file is downloaded.

Some intended UI options:
---------
• drag‑and‑drop folders/songs
• reading ID3 tags (title, artist, album)
• album art extraction
• playlists saved to JSON (or something more appropriate)
• keyboard shortcuts
• system media keys (play/pause/next)
• tray icon with controls
• lyrics + AI connection

Architecture
------------
Components:
- Tauri frontend: HTML/CSS/JavaScript UI served by the Tauri shell.
- Rust backend: handles OneDrive API, download logic, cache management, and exposes a command API to the frontend.
- Cache/storage root: a single app-specific directory containing `settings.json`, `cache/`, `auth/`, and any downloaded/temp data.
- Cache storage: local filesystem cache with metadata stored in a lightweight format.

Data flow:
- User authenticates and selects a OneDrive folder.
- Backend resolves the folder and lists audio files via Microsoft Graph.
- User selects a track.
- Backend downloads the initial bytes using HTTP range requests.
- Frontend begins playback when enough data is buffered.
- Backend continues to fetch upcoming ranges and stores them in the cache.

Key Technologies
----------------
- Tauri: cross-platform desktop shell with Rust backend and web frontend.
- Rust: backend logic, OneDrive integration, download manager, cache manager.
- Microsoft Graph API / OneDrive API: remote file listing and content fetching.
- Local cache: filesystem cache directory with metadata (JSON or SQLite).
- Frontend: lightweight web UI using standard web technologies.

Backend Responsibilities
------------------------
- Authentication:
  - OAuth2 flow with Microsoft Graph.
  - Securely store refresh tokens in app data.
- OneDrive folder handling:
  - Resolve configured folder path to OneDrive folder ID.
  - List audio files and metadata.
- Streaming download:
  - Fetch remote file ranges via HTTP range requests.
  - Expose stream URLs or local temp file paths to the frontend.
- Caching:
  - Store downloaded chunks or completed files under a local cache directory.
  - Track cached ranges and last access times.
  - Simple eviction: max cache size and LRU cleanup.

Frontend Responsibilities
------------------------
- Display authenticated state and configured folder.
- Show song list and cache status.
- Provide playback controls: play, pause, seek, next, previous.
- Display progress and buffering state.
- Communicate with Rust backend through Tauri commands.

MVP2 Connected User Flow
-------------
1. Launch app.
2. Authenticate with OneDrive, store credentials.
3. Choose a OneDrive folder to use as the music library.
4. View the list of audio files.
5. Select a track.
6. Playback begins quickly using progressive download.
7. Continue playback while remaining data downloads and caches locally.
8. Provide settings store (window position, remote location, last played song)

Future Considerations
---------------------
- Better cache metadata and partial-file tracking.
- Support for mobile app or browser-based frontend by reusing backend APIs.
- Search, sorting, playlists.
- Support for additional cloud sources beyond OneDrive.
- More advanced playback and audio format handling.

Next Steps
----------
1. Initialize a Tauri project in `one-cloud-player`.
2. Build the Rust backend skeleton and command API.
3. Implement OneDrive OAuth and folder listing.
4. Add progressive download and cache logic.
5. Create a minimal frontend for track selection and playback.
6. Test on macOS and Windows.

Topics for later
----------
1. If you want to make the stream more robust later, the next improvement is:
- support HTTP range requests / proper Content-Length
- ensure the Rust server keeps the connection stable
- or use a direct  / blob path instead of local HTTP streaming
