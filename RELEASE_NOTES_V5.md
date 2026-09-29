# TouchKeys V5

## Highlights

- Added HTTPS hosting for the phone controller with local TLS certificate generation and certificate download support.
- Added an editor-configurable Sensor / Gyro control with per-axis orientation or angular-velocity modes.
- Added friendly X/Y/Z axis descriptions, Xbox stick/trigger mapping, sensitivity, smoothing, and inversion controls.
- Sensor calculations now happen on the phone; the PC receives normalized analog values only.
- Physical analog-stick touch takes priority over mapped Sensor output, which resumes when the stick is released.
- Added explicit sensor permission activation through the Sensor control’s ENABLE button.

## Browser compatibility

The phone certificate is self-signed for local-LAN use. Browsers may show an unsafe-site warning. Continue through **Learn More**, **Advanced Options**, and **Visit Website / Continue** as appropriate for the browser.

Chrome accepted the explicit sensor permission flow during testing. Safari may still block or omit the native motion permission prompt because its secure-context handling of self-signed LAN certificates differs from Chrome. This is a browser-specific limitation.

## Upgrade notes

1. Install ViGEmBus if it is not already installed.
2. Launch `TouchKeys-V5.exe`.
3. Start the phone server from the desktop monitor.
4. Open the displayed HTTPS URL and complete the browser certificate warning flow.
5. Configure a Sensor / Gyro control in the editor and tap ENABLE on the phone.
