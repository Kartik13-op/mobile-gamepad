# Cleanup stale virtual Xbox 360 controllers
# Run this as Administrator once to clear orphaned ViGEmBus devices.
# After this, the server's shutdown() keeps it clean.
Write-Host "Stopping ViGEmBus driver..."
sc.exe stop ViGEmBus
Start-Sleep -Seconds 3
Write-Host "Starting ViGEmBus driver..."
sc.exe start ViGEmBus
Start-Sleep -Seconds 2
Write-Host "Done! All stale virtual controllers removed."
