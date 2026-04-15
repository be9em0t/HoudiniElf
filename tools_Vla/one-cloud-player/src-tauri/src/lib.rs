mod commands;

use commands::{greet, list_local_audio_files, local_audio_server_port, probe_local_audio_file, read_local_audio_file, validate_audio_directory, LocalAudioServerPort};
use std::{fs::File, io::Cursor, thread};
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

fn start_local_audio_server() -> u16 {
    let server = Server::http("127.0.0.1:0").expect("failed to bind local audio server");
    let port = server
        .server_addr()
        .to_ip()
        .expect("failed to resolve local audio server address")
        .port();
    thread::spawn(move || {
        for request in server.incoming_requests() {
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
                                    Ok(file) => {
                                        let mime = path
                                            .extension()
                                            .and_then(|ext| ext.to_str())
                                            .map(local_audio_mime)
                                            .unwrap_or("application/octet-stream");
                                        let file_size = file.metadata().map(|m| m.len()).ok();
                                        Response::new(
                                            StatusCode(200),
                                            vec![Header::from_bytes(&b"Content-Type"[..], mime).unwrap()],
                                            Box::new(file) as Box<dyn std::io::Read + Send>,
                                            file_size.map(|s| s as usize),
                                            None,
                                        )
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
        }
    });
    port
}


#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let port = start_local_audio_server();
    tauri::Builder::default()
        .manage(LocalAudioServerPort(port))
        .plugin(tauri_plugin_opener::init())
        .invoke_handler(tauri::generate_handler![greet, validate_audio_directory, list_local_audio_files, probe_local_audio_file, read_local_audio_file, local_audio_server_port])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
