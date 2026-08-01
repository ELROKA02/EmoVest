#[cfg(feature = "desktop-updater")]
fn main() -> Result<(), Box<dyn std::error::Error>> {
    use base64::{engine::general_purpose::STANDARD, Engine};
    use minisign_verify::{PublicKey, Signature};
    use std::{env, fs};

    let mut arguments = env::args_os().skip(1);
    let artifact_path = arguments.next().ok_or("falta la ruta del instalador")?;
    let signature_path = arguments.next().ok_or("falta la ruta de la firma")?;
    let encoded_public_key = arguments.next().ok_or("falta la clave pública")?;
    if arguments.next().is_some() {
        return Err("se recibieron argumentos inesperados".into());
    }

    let artifact = fs::read(artifact_path)?;
    let encoded_signature = fs::read_to_string(signature_path)?;
    let public_key_text =
        String::from_utf8(STANDARD.decode(encoded_public_key.to_string_lossy().trim())?)?;
    let signature_text = String::from_utf8(STANDARD.decode(encoded_signature.trim())?)?;
    let public_key = PublicKey::decode(&public_key_text)?;
    let signature = Signature::decode(&signature_text)?;
    public_key.verify(&artifact, &signature, true)?;
    println!("La firma del updater coincide con la clave pública configurada.");
    Ok(())
}

#[cfg(not(feature = "desktop-updater"))]
fn main() {
    eprintln!("Este verificador requiere --features desktop-updater.");
    std::process::exit(2);
}
