//! Bounded JSON readiness receipt. A listening TCP port alone is never readiness.
use std::io::Read;
use std::path::Path;

#[derive(serde::Deserialize)]
#[serde(deny_unknown_fields)]
struct Receipt {
    version: u32,
    instance_id: String,
    origin: String,
    home: String,
    frontend_ready: bool,
}

pub(crate) fn matches(path: &Path, instance: &str, home: &Path, port: u16) -> bool {
    let Ok(file) = std::fs::File::open(path) else {
        return false;
    };
    let mut bytes = Vec::new();
    if file.take(4097).read_to_end(&mut bytes).is_err() || bytes.len() > 4096 {
        return false;
    }
    let Ok(receipt) = serde_json::from_slice::<Receipt>(&bytes) else {
        return false;
    };
    receipt.version == 1
        && receipt.instance_id == instance
        && receipt.origin == format!("http://127.0.0.1:{port}")
        && Path::new(&receipt.home) == home
        && receipt.frontend_ready
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn bounded_launch_specific_contract() {
        let dir = std::env::temp_dir().join(format!("ce-receipt-test-{}", std::process::id()));
        std::fs::create_dir_all(&dir).unwrap();
        let path = dir.join("ready.json");
        let home = dir.join("نصب با فاصله");
        let body = serde_json::json!({"version":1,"instance_id":"123-456",
            "origin":"http://127.0.0.1:8756","home":home.to_str().unwrap(),"frontend_ready":true});
        assert!(!matches(&path, "123-456", &home, 8756));
        std::fs::write(&path, serde_json::to_vec(&body).unwrap()).unwrap();
        assert!(matches(&path, "123-456", &home, 8756));
        assert!(!matches(&path, "other-instance", &home, 8756));
        assert!(!matches(&path, "123-456", &home, 8757));
        assert!(!matches(&path, "123-456", &dir, 8756));
        for (field, value) in [
            ("version", serde_json::json!(2)),
            ("frontend_ready", serde_json::json!(false)),
            ("origin", serde_json::json!("https://untrusted.example")),
            ("unknown", serde_json::json!(true)),
        ] {
            let mut changed = body.clone();
            changed[field] = value;
            std::fs::write(&path, serde_json::to_vec(&changed).unwrap()).unwrap();
            assert!(!matches(&path, "123-456", &home, 8756));
        }
        for invalid in [vec![b'x'; 4097], b"{}".to_vec(), b"not json".to_vec()] {
            std::fs::write(&path, invalid).unwrap();
            assert!(!matches(&path, "123-456", &home, 8756));
        }
        std::fs::remove_dir_all(dir).unwrap();
    }
}
