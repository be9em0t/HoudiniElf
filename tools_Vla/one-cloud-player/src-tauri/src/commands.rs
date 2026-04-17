use base64::{engine::general_purpose, Engine as _};
use serde::{Deserialize, Serialize};
use std::{fs, path::{Path, PathBuf}};
use tauri::State;

#[derive(Serialize)]
pub struct AudioTrack {
    pub name: String,
    pub path: String,
    pub size: u64,
    pub extension: String,
}

#[derive(Serialize)]
pub struct AudioProbe {
    pub exists: bool,
    pub is_file: bool,
    pub size: u64,
    pub sample_hex: String,
}

#[derive(Clone, Serialize, Deserialize, Default)]
#[serde(rename_all = "camelCase")]
pub struct AppSettings {
    pub last_open_folder: Option<String>,
    pub last_played_track: Option<String>,
    pub window_position: Option<[i32; 2]>,
    pub window_size: Option<[u32; 2]>,
}

#[derive(Clone)]
pub struct AppStorage {
    pub root: PathBuf,
}

fn app_settings_path(state: &State<'_, AppStorage>) -> PathBuf {
    state.root.join("settings.json")
}

#[tauri::command]
pub fn load_settings(state: State<'_, AppStorage>) -> Result<AppSettings, String> {
    let path = app_settings_path(&state);
    if !path.exists() {
        return Ok(AppSettings::default());
    }
    let json = fs::read_to_string(&path).map_err(|e| format!("Failed to read settings: {}", e))?;
    serde_json::from_str(&json).map_err(|e| format!("Failed to parse settings: {}", e))
}

#[tauri::command]
pub fn save_settings(settings: AppSettings, state: State<'_, AppStorage>) -> Result<(), String> {
    fs::create_dir_all(&state.root).map_err(|e| format!("Failed to create storage root: {}", e))?;
    let json = serde_json::to_string_pretty(&settings).map_err(|e| format!("Failed to serialize settings: {}", e))?;
    fs::write(app_settings_path(&state), json).map_err(|e| format!("Failed to write settings: {}", e))
}

#[tauri::command]
pub fn get_storage_root(state: State<'_, AppStorage>) -> String {
    state.root.display().to_string()
}

#[tauri::command]
pub fn greet(name: &str) -> String {
    format!("Hello, {}! You've been greeted from Rust!", name)
}

#[tauri::command]
pub fn validate_audio_directory(dir: &str) -> bool {
    Path::new(dir).is_dir()
}

#[tauri::command]
pub fn list_local_audio_files(dir: &str) -> Result<Vec<AudioTrack>, String> {
    let path = Path::new(dir);
    if !path.exists() {
        return Err(format!("Directory not found: {}", dir));
    }
    if !path.is_dir() {
        return Err(format!("Path is not a directory: {}", dir));
    }

    let mut tracks = Vec::new();
    for entry in fs::read_dir(path).map_err(|e| format!("Failed to read directory: {}", e))? {
        let entry = entry.map_err(|e| format!("Failed to read directory entry: {}", e))?;
        let metadata = entry
            .metadata()
            .map_err(|e| format!("Failed to read file metadata: {}", e))?;
        if !metadata.is_file() {
            continue;
        }

        let file_path = entry.path();
        let extension = file_path
            .extension()
            .and_then(|ext| ext.to_str())
            .map(|ext| ext.to_lowercase());

        let supported = matches!(extension.as_deref(),
            Some("mp3") | Some("wav") | Some("flac") | Some("m4a") | Some("aac") | Some("ogg") | Some("opus")
        );

        if !supported {
            continue;
        }

        let name = file_path
            .file_name()
            .and_then(|name| name.to_str())
            .unwrap_or_default()
            .to_string();
        let extension = extension.unwrap_or_default();

        tracks.push(AudioTrack {
            name,
            path: file_path.display().to_string(),
            size: metadata.len(),
            extension,
        });
    }

    tracks.sort_by(|a, b| a.name.to_lowercase().cmp(&b.name.to_lowercase()));
    Ok(tracks)
}

#[tauri::command]
pub fn probe_local_audio_file(path: &str) -> Result<AudioProbe, String> {
    let path = Path::new(path);
    let exists = path.exists();
    let is_file = path.is_file();
    let metadata = path
        .metadata()
        .map_err(|e| format!("Failed to read file metadata: {}", e))?;
    let size = metadata.len();

    let mut sample_hex = String::new();
    if is_file {
        let content = fs::read(path).map_err(|e| format!("Failed to read file: {}", e))?;
        let sample = &content[..content.len().min(20)];
        sample_hex = sample.iter().map(|b| format!("{:02x}", b)).collect::<Vec<_>>().join(" ");
    }

    Ok(AudioProbe {
        exists,
        is_file,
        size,
        sample_hex,
    })
}

#[tauri::command]
pub fn read_local_audio_file(path: &str) -> Result<String, String> {
    let path = Path::new(path);
    if !path.exists() {
        return Err(format!("File not found: {}", path.display()));
    }
    if !path.is_file() {
        return Err(format!("Path is not a file: {}", path.display()));
    }

    let bytes = fs::read(path).map_err(|e| format!("Failed to read file: {}", e))?;
    Ok(general_purpose::STANDARD.encode(&bytes))
}

#[derive(Serialize)]
pub struct LocalAudioServerPort(pub u16);

#[tauri::command]
pub fn local_audio_server_port(state: tauri::State<'_, LocalAudioServerPort>) -> u16 {
    state.0
}
