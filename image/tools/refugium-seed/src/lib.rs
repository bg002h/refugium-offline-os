mod draws;

use bip39::{Language, Mnemonic};
use std::slice;
use std::str;

/// Decode physical entropy into BIP39 word indices for the Wayland view.
///
/// # Safety
/// `input` must be non-null and readable for `len` bytes. `output` must
/// point to 24 aligned, writable slots disjoint from the input.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn seed_generate(
    method: u8,
    word_count: usize,
    input: *const u8,
    len: usize,
    output: *mut u16,
) -> u8 {
    if !matches!(word_count, 12 | 24) || len > 1024 {
        return 1;
    }
    // The display supplies a live input buffer and 24 writable index slots.
    let Ok(input) = str::from_utf8(unsafe { slice::from_raw_parts(input, len) }) else {
        return 1;
    };
    let bits = word_count * 32 / 3;
    let entropy = match method {
        1 => draws::dice_hand(input, bits),
        2 => draws::dice_hashed(input, bits),
        3 => draws::coins(input, bits),
        4 => draws::pills(input, bits),
        _ => return 1,
    };
    let entropy = match entropy {
        Ok(entropy) => entropy,
        Err(draws::Refusal::DiceFew | draws::Refusal::Empty) => return 2,
        Err(draws::Refusal::DiceMany) => return 3,
        Err(draws::Refusal::NotMixed) => return 4,
        Err(draws::Refusal::Invalid) => return 1,
    };
    let Ok(phrase) = Mnemonic::from_entropy_in(Language::English, &entropy) else {
        return 1;
    };
    for (i, word) in phrase.word_indices().enumerate() {
        unsafe { output.add(i).write(word as u16) };
    }
    0
}

#[unsafe(no_mangle)]
pub extern "C" fn seed_word(index: u16) -> *const u8 {
    Language::English.word_list()[usize::from(index)].as_ptr()
}

#[unsafe(no_mangle)]
pub extern "C" fn seed_word_len(index: u16) -> usize {
    Language::English.word_list()[usize::from(index)].len()
}

#[cfg(test)]
mod tests {
    use super::*;
    use sha2::{Digest, Sha256};

    fn check(method: u8, length: usize, text: &str, expected: &[u8]) {
        let mut indices = [u16::MAX; 24];
        // This fixture contains synthetic entropy. No phrase is printed.
        let result = unsafe {
            seed_generate(
                method,
                length,
                text.as_ptr(),
                text.len(),
                indices.as_mut_ptr(),
            )
        };
        assert_eq!(result, 0);
        let mnemonic = Mnemonic::from_entropy(expected).expect("valid test entropy");
        assert!(
            indices[..length]
                .iter()
                .map(|i| usize::from(*i))
                .eq(mnemonic.word_indices())
        );
        assert!(indices[length..].iter().all(|i| *i == u16::MAX));
    }

    #[test]
    fn every_method_at_both_lengths() {
        for length in [12, 24] {
            let bytes = length * 4 / 3;
            check(1, length, &"3141".repeat(bytes), &vec![0x8c; bytes]);
            check(3, length, &"HTHTTHTT".repeat(bytes), &vec![0xa4; bytes]);
            let dice = "16554326".repeat(if length == 12 { 7 } else { 13 });
            let hash = Sha256::digest(dice.as_bytes());
            check(2, length, &dice, &hash[..bytes]);

            let words = Language::English.word_list();
            let count = if length == 12 { 11 } else { 22 };
            let mut input = format!("HTTTTTT {}", words[0..count].join(" "));
            if length == 24 {
                input.push_str(" TTTTTTH");
            }
            let bits = (0..7)
                .map(|i| i == 0)
                .chain((0..count).flat_map(|i| (0..11).rev().map(move |bit| i & (1 << bit) != 0)))
                .chain((0..if length == 24 { 7 } else { 0 }).map(|i| i == 6))
                .collect::<Vec<_>>();
            let expected = bits
                .chunks_exact(8)
                .map(|chunk| {
                    chunk
                        .iter()
                        .fold(0u8, |byte, bit| (byte << 1) | u8::from(*bit))
                })
                .collect::<Vec<_>>();
            check(4, length, &input, &expected);
        }
    }

    #[test]
    fn rejects_short_and_uniform_draws_without_writing_output() {
        let mut indices = [u16::MAX; 24];
        for (method, input) in [
            (1, "123".to_owned()),
            (2, "1".repeat(100)),
            (3, "H".repeat(256)),
            (4, "HTHTHTH invalid".to_owned()),
        ] {
            let result = unsafe {
                seed_generate(
                    method,
                    24,
                    input.as_ptr(),
                    input.len(),
                    indices.as_mut_ptr(),
                )
            };
            assert_ne!(result, 0);
            assert!(indices.iter().all(|i| *i == u16::MAX));
        }
    }
}
