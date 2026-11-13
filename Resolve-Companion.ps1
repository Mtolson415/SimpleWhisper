function Resolve-DictationCompanion {
    foreach ($relativePath in @(
        'portable\v0.5.3\SimpleWhisper\SimpleWhisper.exe',
        'portable\SimpleWhisper\SimpleWhisper.exe'
    )) {
        $candidatePath = Join-Path $PSScriptRoot $relativePath
        if (Test-Path -LiteralPath $candidatePath) { return $candidatePath }
    }
    return $null
}
