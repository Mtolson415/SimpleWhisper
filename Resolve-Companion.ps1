function Resolve-DictationCompanion {
    foreach ($relativePath in @(
        'portable\v0.3.1\LocalWhisperDictation\LocalWhisperDictation.exe',
        'portable\LocalWhisperDictation\LocalWhisperDictation.exe'
    )) {
        $candidatePath = Join-Path $PSScriptRoot $relativePath
        if (Test-Path -LiteralPath $candidatePath) { return $candidatePath }
    }
    return $null
}
