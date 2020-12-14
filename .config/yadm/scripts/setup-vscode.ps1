foreach($line in Get-Content .\extensions) {
    code --install-extension $line
}
