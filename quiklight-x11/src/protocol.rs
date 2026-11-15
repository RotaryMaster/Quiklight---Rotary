use anyhow::{ensure, Result};
use std::io::Write;

fn checksum(data: &[u8]) -> u8 {
    data.iter().fold(0u8, |acc, &b| acc.wrapping_add(b))
}

fn write_hid(out: &mut impl Write, packet: &[u8]) -> Result<()> {
    let mut offset = 0;
    while offset < packet.len() {
        let end = (offset + 64).min(packet.len());
        let chunk = &packet[offset..end];
        let mut buf = [0u8; 65];
        buf[1..1 + chunk.len()].copy_from_slice(chunk); // buf[0] = 0x00 (report ID)
        out.write_all(&buf)?;
        offset += 64;
    }
    Ok(())
}

fn rb(msg_id: u8, action: u8, payload: &[u8]) -> Vec<u8> {
    let total = 5 + payload.len() + 1;
    let mut out = Vec::with_capacity(total);
    out.extend_from_slice(&[b'R', b'B', total as u8, msg_id, action]);
    out.extend_from_slice(payload);
    let cs = checksum(&out);
    out.push(cs);
    out
}

fn frame(msg_id: u8, leds: &[(u8, u8, u8)]) -> Vec<u8> {
    let payload_len = leds.len() * 5;
    let total = 6 + payload_len + 1;
    let mut out = Vec::with_capacity(total);
    out.extend_from_slice(&[
        b'S',
        b'C',
        ((total >> 8) & 0xFF) as u8,
        (total & 0xFF) as u8,
        msg_id,
        128,
    ]);
    for (i, &(r, g, b)) in leds.iter().enumerate() {
        let n = (i + 1) as u8;
        out.extend_from_slice(&[n, r, g, b, n]);
    }
    let cs = checksum(&out);
    out.push(cs);
    out
}

// Device sections use one-based LED indices. 0xFE is the firmware's
// last-section marker, so never wrap an LED index into u8.
const MAX_LEDS: usize = 253;

pub fn init(out: &mut impl Write, brightness: u8, n_leds: usize) -> Result<u8> {
    ensure!((1..=MAX_LEDS).contains(&n_leds),
            "Quantidade de LEDs inválida para este controlador: {n_leds} (1..={MAX_LEDS})");
    let last = n_leds as u8;
    let mut mid: u8 = 0;
    write_hid(out, &rb(mid, 147, &[0]))?;
    mid = mid.wrapping_add(1);
    write_hid(out, &rb(mid, 135, &[brightness]))?;
    mid = mid.wrapping_add(1);
    // Previously hardcoded as 63,64, which became inconsistent when the
    // user selected any other LED count.
    write_hid(out, &rb(mid, 134, &[1, 85, 85, 85, last, last + 1, 0, 0, 0, 254]))?;
    mid = mid.wrapping_add(1);
    write_hid(out, &frame(mid, &vec![(0, 0, 0); n_leds]))?;
    mid = mid.wrapping_add(1);
    Ok(mid)
}

pub fn send_frame(out: &mut impl Write, msg_id: u8, leds: &[(u8, u8, u8)]) -> Result<()> {
    ensure!(leds.len() <= MAX_LEDS,
            "Quantidade de LEDs excede o protocolo HID: {}", leds.len());
    write_hid(out, &frame(msg_id, leds))
}

/// Firmware's own turnOffLight (RB action 0x97), independent of current
/// LED count. Safer than resetting the controller with a stale layout.
pub fn turn_off(out: &mut impl Write) -> Result<()> {
    write_hid(out, &rb(0, 0x97, &[0]))
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn init_uses_selected_led_count() {
        for leds in [62usize, 63usize, 100usize] {
            let mut bytes = Vec::new();
            init(&mut bytes, 255, leds).unwrap();
            // Third HID report is the setSectionLED packet, preceded by report id 0.
            let section = &bytes[2 * 65..3 * 65];
            assert_eq!(&section[1..6], &[b'R', b'B', 16, 2, 134]);
            assert_eq!(section[10], leds as u8);
            assert_eq!(section[11], leds as u8 + 1);
        }
    }

    #[test]
    fn turn_off_is_independent_of_led_count() {
        let mut bytes = Vec::new();
        turn_off(&mut bytes).unwrap();
        assert_eq!(&bytes[1..7], &[b'R', b'B', 7, 0, 0x97, 0]);
    }
}

