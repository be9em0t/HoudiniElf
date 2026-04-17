mod commands;

use commands::{greet, get_storage_root, load_settings, list_local_audio_files, local_audio_server_port, probe_local_audio_file, read_local_audio_file, save_settings, set_ui_window_mode, validate_audio_directory, AppStorage, LocalAudioServerPort};
use std::{fs, fs::File, io::{Cursor, Read, Seek, SeekFrom}, path::PathBuf, thread};
use tauri::Manager;
use tiny_http::{Header, Response, Server, StatusCode};
use url::Url;

fn local_audio_mime(extension: &str) -> &'static str {
    match extension.to_lowercase().as_str() {
        "mp3" => "audio/mpeg",
        "wav" => "audio/wav",
        "flac" => "audio/flac",
        "m4a" => "audio/mp4",
        "aac" => "audio/aac",
        "ogg" => "audio/ogg",
        "opus" => "audio/opus",
        _ => "application/octet-stream",
    }
}

fn local_text_response(status: StatusCode, body: impl Into<String>) -> Response<Box<dyn std::io::Read + Send>> {
    let body = body.into();
    Response::new(
        status,
        vec![Header::from_bytes(&b"Content-Type"[..], b"text/plain; charset=utf-8").unwrap()],
        Box::new(Cursor::new(body.clone().into_bytes())),
        Some(body.len()),
        None,
    )
}

fn parse_range_header(range_header: &str, file_size: u64) -> Option<(u64, u64)> {
    if !range_header.starts_with("bytes=") {
        return None;
    }

    let range = &range_header[6..];
    let (start_text, end_text) = range.split_once('-')?;

    let start = if start_text.is_empty() {
        None
    } else {
        start_text.parse::<u64>().ok()
    };
    let end = if end_text.is_empty() {
        None
    } else {
        end_text.parse::<u64>().ok()
    };

    match (start, end) {
        (Some(start), Some(end)) if start <= end && end < file_size => Some((start, end)),
        (Some(start), None) if start < file_size => Some((start, file_size - 1)),
        (None, Some(suffix_len)) if suffix_len > 0 && suffix_len <= file_size => {
            Some((file_size - suffix_len, file_size - 1))
        }
        _ => None,
    }
}

fn app_storage_root(_app: &tauri::AppHandle) -> PathBuf {
    let exe_path = std::env::current_exe().expect("failed to resolve current executable path");
    let root = exe_path
        .parent()
        .expect("failed to get executable directory")
        .join("one-cloud-player-data");

    fs::create_dir_all(&root).expect("failed to create portable storage root");
    let _ = fs::create_dir_all(root.join("cache"));
    let _ = fs::create_dir_all(root.join("auth"));
    let _ = fs::create_dir_all(root.join("downloads"));
    root
}

fn start_local_audio_server() -> u16 {
    let server = Server::http("127.0.0.1:0").expect("failed to bind local audio server");
    let port = server
        .server_addr()
        .to_ip()
        .expect("failed to resolve local audio server address")
        .port();
    thread::spawn(move || {
        for request in server.incoming_requests() {
            thread::spawn(move || {
                let url = format!("http://localhost{}", request.url());
                let response = match Url::parse(&url) {
                    Ok(parsed) if parsed.path() == "/track" => {
                        let path_param = parsed.query_pairs().find(|(key, _)| key == "path");
                        match path_param {
                            Some((_, value)) => {
                                let path_string = value.to_string();
                                let path = std::path::Path::new(&path_string);
                                if !path.exists() {
                                    local_text_response(StatusCode(404), "File not found")
                                } else if !path.is_file() {
                                    local_text_response(StatusCode(400), "Path is not a file")
                                } else {
                                    match File::open(path) {
                                        Ok(mut file) => {
                                            let file_size = file.metadata().map(|m| m.len()).unwrap_or(0);
                                            let mime = path
                                                .extension()
                                                .and_then(|ext| ext.to_str())
                                                .map(local_audio_mime)
                                                .unwrap_or("application/octet-stream");
                                            let range_header = request
                                                .headers()
                                                .iter()
                                                .find(|h| h.field.equiv("Range"))
                                                .and_then(|h| h.value.as_str().parse::<String>().ok())
                                                .map(|s| s.to_string());
                                            let (status, reader, content_length, headers) = if let Some(range) = range_header.as_deref().and_then(|h| parse_range_header(h, file_size)) {
                                                let (start, end) = range;
                                                let length = (end - start + 1) as usize;
                                                file.seek(SeekFrom::Start(start)).ok();
                                                let reader = Box::new(file.take(length as u64)) as Box<dyn Read + Send>;
                                                let mut headers = vec![Header::from_bytes(&b"Content-Type"[..], mime).unwrap()];
                                                headers.push(Header::from_bytes(&b"Content-Length"[..], length.to_string().as_bytes()).unwrap());
                                                headers.push(Header::from_bytes(&b"Content-Range"[..], format!("bytes {}-{}/{}", start, end, file_size).as_bytes()).unwrap());
                                                (StatusCode(206), reader, Some(length), headers)
                                            } else {
                                                let reader = Box::new(file) as Box<dyn Read + Send>;
                                                let headers = vec![Header::from_bytes(&b"Content-Type"[..], mime).unwrap()];
                                                (StatusCode(200), reader, Some(file_size as usize), headers)
                                            };
                                            Response::new(status, headers, reader, content_length, None)
                                        }
                                        Err(err) => local_text_response(StatusCode(500), format!("Failed to open file: {}", err)),
                                    }
                                }
                            }
                            None => local_text_response(StatusCode(400), "Missing path parameter"),
                        }
                    }
                    _ => local_text_response(StatusCode(404), "Not found"),
                };
                let _ = request.respond(response);
            });
        }
    });
    port
}


#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .setup(|app| {
            let storage_root = app_storage_root(&app.handle());
            app.manage(AppStorage { root: storage_root });
            Ok(())
        })
        .manage(LocalAudioServerPort(start_local_audio_server()))
        .plugin(tauri_plugin_opener::init())
        .invoke_handler(tauri::generate_handler![greet, validate_audio_directory, list_local_audio_files, probe_local_audio_file, read_local_audio_file, local_audio_server_port, get_storage_root, load_settings, save_settings, set_ui_window_mode])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
