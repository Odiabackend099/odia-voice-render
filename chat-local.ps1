Write-Host "ODIA Voice Chat — type and press Enter. Press just q then Enter to quit."
$last = "How you dey? We don ready to run am!"
while ($true) {
  $t = Read-Host "You"
  if ($t -eq 'q') { break }
  if ([string]::IsNullOrWhiteSpace($t)) {
    $t = $last  # use previous text when you just hit Enter
  } else {
    $last = $t
  }
  powershell -NoProfile -ExecutionPolicy Bypass -File ".\say.ps1" -Text $t | Out-Host
}
