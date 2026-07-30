#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

fn main() {
    if let Err(error) = emovest_desktop_lib::run() {
        eprintln!("No se pudo inicializar EmoVest Desktop: {error}");
        std::process::exit(1);
    }
}
