//! Entropy extraction adapted from mr-sitting at 5de47c92 (draws.rs).
use bip39::Language;
use sha2::{Digest, Sha256};
use zeroize::Zeroizing;

#[derive(Debug)]
pub enum Refusal {
    Empty,
    Invalid,
    DiceFew,
    DiceMany,
    NotMixed,
}

fn chars(input: &str) -> Zeroizing<Vec<char>> {
    let mut out = Zeroizing::new(Vec::with_capacity(input.len()));
    out.extend(input.chars().filter(|c| !c.is_ascii_whitespace()));
    out
}

fn pack(bits: &[bool]) -> Zeroizing<Vec<u8>> {
    let mut out = Zeroizing::new(vec![0u8; bits.len().div_ceil(8)]);
    for (i, b) in bits.iter().enumerate() {
        if *b {
            out[i / 8] |= 0x80 >> (i % 8);
        }
    }
    out
}

pub fn dice_hand(rolls: &str, bits: usize) -> Result<Zeroizing<Vec<u8>>, Refusal> {
    let c = chars(rolls);
    if c.is_empty() {
        return Err(Refusal::Empty);
    }
    if c.iter().any(|c| !('1'..='6').contains(c)) {
        return Err(Refusal::Invalid);
    }
    let mut b: Zeroizing<Vec<bool>> = Zeroizing::new(Vec::with_capacity(bits + 1));
    let mut reached = None;
    for (i, c) in c.iter().enumerate() {
        match c {
            '1' => b.extend([false, false]),
            '2' => b.extend([false, true]),
            '3' => b.extend([true, false]),
            '4' => b.extend([true, true]),
            '5' => b.push(false),
            _ => b.push(true),
        }
        if b.len() >= bits {
            reached = Some(i + 1);
            break;
        }
    }
    let Some(k) = reached else {
        return Err(Refusal::DiceFew);
    };
    if c.len() > k {
        return Err(Refusal::DiceMany);
    }
    if c.iter().all(|d| *d == c[0]) {
        return Err(Refusal::NotMixed);
    }
    b.truncate(bits);
    Ok(pack(&b))
}

pub fn dice_hashed(input: &str, bits: usize) -> Result<Zeroizing<Vec<u8>>, Refusal> {
    let mut digits = Zeroizing::new(Vec::with_capacity(input.len()));
    digits.extend(input.bytes().filter(|c| !c.is_ascii_whitespace()));
    let minimum = if bits == 128 { 50 } else { 100 };
    if digits.iter().any(|c| !(b'1'..=b'6').contains(c)) {
        return Err(Refusal::Invalid);
    }
    if digits.len() < minimum {
        return Err(Refusal::DiceFew);
    }
    if digits.iter().all(|c| *c == digits[0]) {
        return Err(Refusal::NotMixed);
    }
    let mut digest = Sha256::digest(&*digits);
    let out = Zeroizing::new(digest[..bits / 8].to_vec());
    zeroize::Zeroize::zeroize(digest.as_mut_slice());
    Ok(out)
}

pub fn coins(input: &str, bits: usize) -> Result<Zeroizing<Vec<u8>>, Refusal> {
    let mut out = Zeroizing::new(Vec::with_capacity(bits));
    append_flips(&mut out, input, bits)?;
    finish(&out)
}

fn append_flips(out: &mut Vec<bool>, input: &str, count: usize) -> Result<(), Refusal> {
    let flips = chars(input);
    if flips.len() != count {
        return Err(Refusal::Invalid);
    }
    for c in flips.iter() {
        match c {
            'h' | 'H' | '1' => out.push(true),
            't' | 'T' | '0' => out.push(false),
            _ => return Err(Refusal::Invalid),
        }
    }
    Ok(())
}

pub fn pills(input: &str, bits: usize) -> Result<Zeroizing<Vec<u8>>, Refusal> {
    let pills = if bits == 128 { 11 } else { 22 };
    let mut parts = input.split_ascii_whitespace();
    let mut out = Zeroizing::new(Vec::with_capacity(bits));
    append_flips(&mut out, parts.next().ok_or(Refusal::Invalid)?, 7)?;
    let mut indices = Zeroizing::new(Vec::with_capacity(pills));
    for _ in 0..pills {
        let word = parts.next().ok_or(Refusal::Invalid)?;
        let index = Language::English.find_word(word).ok_or(Refusal::Invalid)?;
        indices.push(index);
        out.extend((0..11).rev().map(|bit| index & (1 << bit) != 0));
    }
    if indices.iter().all(|i| *i == indices[0]) {
        return Err(Refusal::NotMixed);
    }
    if bits == 256 {
        append_flips(&mut out, parts.next().ok_or(Refusal::Invalid)?, 7)?;
    }
    if parts.next().is_some() {
        return Err(Refusal::Invalid);
    }
    finish(&out)
}

fn finish(bits: &[bool]) -> Result<Zeroizing<Vec<u8>>, Refusal> {
    if bits.iter().all(|b| *b == bits[0]) {
        return Err(Refusal::NotMixed);
    }
    Ok(pack(bits))
}
