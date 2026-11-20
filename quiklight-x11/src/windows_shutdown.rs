//! Windows-only, in-process shutdown notification IPC.
//! The Qt tray signals named session-local Win32 events at WM_ENDSESSION;
//! the already-running backend turns off LEDs using its OPEN USB HID handles.
//! No CreateProcess/taskkill/new DLL loading during OS shutdown.
use std::ffi::c_void;
use std::ptr::null;
use std::sync::OnceLock;

type Handle = *mut c_void;
const WAIT_OBJECT_0: u32 = 0;
const REQUEST_NAME: &str = "Local\\QuiklightShutdownRequestV1";
const ACK_NAME: &str = "Local\\QuiklightShutdownAckV1";
static EVENTS: OnceLock<(usize, usize)> = OnceLock::new();

#[link(name = "kernel32")]
extern "system" {
    fn CreateEventW(
        event_attributes: *const c_void,
        manual_reset: i32,
        initial_state: i32,
        name: *const u16,
    ) -> Handle;
    fn ResetEvent(event: Handle) -> i32;
    fn SetEvent(event: Handle) -> i32;
    fn WaitForSingleObject(handle: Handle, milliseconds: u32) -> u32;
    fn CloseHandle(handle: Handle) -> i32;
    fn SetProcessShutdownParameters(level: u32, flags: u32) -> i32;
}

fn wide(s: &str) -> Vec<u16> {
    s.encode_utf16().chain(std::iter::once(0)).collect()
}

pub fn initialize() {
    // Default Windows application priority is 0x280. A lower value means
    // shutdown later: the tray sends the request before this backend exits.
    // This is only a relative priority, never an absolute shutdown guarantee.
    unsafe {
        if SetProcessShutdownParameters(0x180, 0) == 0 {
            eprintln!("Windows shutdown IPC: could not adjust shutdown priority.");
        }
        let request = CreateEventW(null(), 1, 0, wide(REQUEST_NAME).as_ptr());
        let ack = CreateEventW(null(), 1, 0, wide(ACK_NAME).as_ptr());
        if request.is_null() || ack.is_null() {
            if !request.is_null() { CloseHandle(request); }
            if !ack.is_null() { CloseHandle(ack); }
            eprintln!("Windows shutdown IPC: could not create session-local events.");
            return;
        }
        // Named events can survive while another process holds them.
        // A new backend instance must never inherit a stale shutdown request.
        ResetEvent(request);
        ResetEvent(ack);
        if EVENTS.set((request as usize, ack as usize)).is_err() {
            CloseHandle(request);
            CloseHandle(ack);
            return;
        }
        eprintln!("Windows shutdown IPC ready: session-local request/ack events.");
    }
}

pub fn requested() -> bool {
    let Some(&(request, _)) = EVENTS.get() else { return false; };
    unsafe { WaitForSingleObject(request as Handle, 0) == WAIT_OBJECT_0 }
}

pub fn acknowledge(blackout_succeeded: bool) {
    if let Some(&(_, ack)) = EVENTS.get() {
        if blackout_succeeded {
            unsafe { SetEvent(ack as Handle); }
            eprintln!("Windows shutdown IPC blackout acknowledged.");
        } else {
            eprintln!("Windows shutdown IPC blackout FAILED; no acknowledgment.");
        }
    }
}
