# TouchKeys V5.1

TouchKeys V5.1 expands the phone controller into a more flexible local control surface and adds synchronized desktop media streaming.

## Highlights

- Added synchronized PC screen and speaker-audio streaming over WebRTC.
- Reduced streaming startup delay and aligned audio/video timestamps to a shared clock.
- Added a plus-shaped D-pad control with independent bindings for up, down, left, and right.
- D-pad directions can trigger Xbox buttons, keyboard keys, or mouse buttons.
- Added joystick output modes for Xbox analog input, directional digital keys, and mouse cursor movement.
- Added configurable joystick direction bindings and mouse sensitivity.
- Added gyro-to-mouse cursor control through the Sensor / Gyro editor.
- Fixed the triggers to purely output analog values when dragged with finger in any direction. The digital mode in its properties makes the triggers output only static digital values when pressed, and the analog mode makes them output analog values when dragged with finger in any direction.
- Added mouse left, right, and middle button bindings with safe press/release cleanup.
- Added layout preset sharing from the desktop monitor.
- Added layout importing through file selection, drag-and-drop, or pasted JSON.
- Imported layouts are appended without replacing the current layout and receive collision-safe page names and IDs.
- Existing layout JSON remains compatible; new control properties are optional and older controls continue to load normally.

## Upgrade notes

1. Install or update the ViGEmBus driver if needed.
2. Download and launch `TouchKeys-V5.1.exe`.
3. Start the phone server from the desktop monitor.
4. Connect the phone and PC to the same Wi-Fi network.
5. Open the displayed HTTPS address or scan the QR code.

For PC audio playback on the phone, Safari and other mobile browsers may require one tap on the controller to unlock audio playback.

## Release artifacts

- `TouchKeys-V5.1.exe` — standalone Windows application.
- `ViGEmBus_1.22.0_x64_x86_arm64.exe` — required virtual Xbox controller driver.
