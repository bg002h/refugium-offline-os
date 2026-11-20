//! Build in the pinned mr-codec source tree. Restrict this program to a nonprivileged user.
use mr_codec::sitting::{handback, plan};
use sha2::{Digest, Sha256};
use std::io::{self, Read};
use std::process::ExitCode;

fn inspect(args: &[String], input: &[u8]) -> Option<String> {
    match args {
        [kind, id] if kind == "plan" => {
            let item = plan::parse(input).ok()?;
            if item.plan_id != *id || plan::write(&item) != input {
                return None;
            }
            let temperature = if item.hot.is_some() { "hot" } else { "cold" };
            Some(format!("plan {id} {temperature}"))
        }
        [kind, id, plan_path] if kind == "handback" => {
            let plan_bytes = std::fs::read(plan_path).ok()?;
            let submitted = plan::parse(&plan_bytes).ok()?;
            let answer = handback::parse(input).ok()?;
            let digest = format!("{:x}", Sha256::digest(&plan_bytes));
            if submitted.plan_id != *id
                || answer.plan_id != *id
                || answer.network != submitted.network
                || answer.plan_sha256 != digest
                || handback::write(&answer) != input
            {
                return None;
            }
            Some(format!("handback {id}"))
        }
        _ => None,
    }
}

fn main() -> ExitCode {
    let args: Vec<String> = std::env::args().skip(1).collect();
    let mut data = Vec::new();
    if io::stdin().read_to_end(&mut data).is_ok() {
        if let Some(public_metadata) = inspect(&args, &data) {
            println!("{public_metadata}");
            return ExitCode::SUCCESS;
        }
    }
    ExitCode::from(2)
}
