"""Exercise the real startup worker with isolated app files and fake Docker.

No services, microphone, installed app or user settings are touched.
"""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


@unittest.skipUnless(sys.platform == 'win32', 'Windows PowerShell startup worker')
class StartupTests(unittest.TestCase):
    def run_worker(self, scenario):
        source = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            shutil.copy(source / 'Start-DictationWorker.ps1', root)
            (root / '.env').write_text('WHISPER_MODEL_DIR=synthetic')
            (root / 'Resolve-Companion.ps1').write_text(
                "function Resolve-DictationCompanion { Join-Path $PSScriptRoot 'fake.exe' }")
            script = r'''
param($Scenario)
$ErrorActionPreference = 'Stop'
$global:Calls = [Collections.Generic.List[string]]::new()
function Get-CimInstance {
    if ($Scenario -eq 'already-open') {
        [pscustomobject]@{ExecutablePath=(Join-Path $PSScriptRoot 'fake.exe'); CommandLine='fake.exe'}
    }
}
function docker {
    $command = $args -join ' '
    $global:Calls.Add($command)
    $global:LASTEXITCODE = 0
    if (($Scenario -eq 'docker-fails' -and $command -like 'desktop*') -or
        ($Scenario -eq 'model-fails' -and $command -like '*up*whisper')) {
        $global:LASTEXITCODE = 1
        'Synthetic startup failure'
    }
}
function Start-Process {
    $process = [pscustomobject]@{Id=999999; HasExited=($Scenario -eq 'app-exits'); MainWindowHandle=123; Responding=$true}
    $process | Add-Member ScriptMethod Refresh {}
    return $process
}
$state = [hashtable]::Synchronized(@{Stage=0; Done=$false; Failed=$false; Detail=''; AlreadyOpen=$false})
& (Join-Path $PSScriptRoot 'Start-DictationWorker.ps1') -State $state
@{State=$state; Calls=@($global:Calls.ToArray())} | ConvertTo-Json -Depth 5 -Compress
'''
            (root / 'test.ps1').write_text(script)
            result = subprocess.run(
                ['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'RemoteSigned',
                 '-File', str(root / 'test.ps1'), scenario],
                capture_output=True, text=True, timeout=15,
                creationflags=subprocess.CREATE_NO_WINDOW)
            self.assertEqual(result.returncode, 0, result.stderr)
            return json.loads(result.stdout)

    def test_success_waits_for_model_then_gateway_then_toolbar(self):
        result = self.run_worker('success')
        self.assertTrue(result['State']['Done'])
        self.assertFalse(result['State']['Failed'])
        self.assertEqual(result['State']['Stage'], 5)
        self.assertIn('desktop start', result['Calls'][0])
        self.assertTrue(result['Calls'][2].endswith('whisper'))
        self.assertTrue(result['Calls'][3].endswith('dictation'))

    def test_docker_failure_does_not_touch_containers(self):
        result = self.run_worker('docker-fails')
        self.assertTrue(result['State']['Failed'])
        self.assertTrue(result['State']['Done'])
        self.assertEqual(result['State']['Stage'], 1)
        self.assertEqual(len(result['Calls']), 1)
        self.assertIn('Synthetic startup failure', result['State']['Detail'])

    def test_model_failure_stops_only_owned_services(self):
        result = self.run_worker('model-fails')
        self.assertTrue(result['State']['Failed'])
        self.assertEqual(result['State']['Stage'], 2)
        self.assertEqual(result['Calls'][-1], 'compose stop --timeout 10 dictation whisper')
        self.assertFalse(any('--no-deps' in item for item in result['Calls']))

    def test_app_exit_is_failure_and_cleans_up(self):
        result = self.run_worker('app-exits')
        self.assertTrue(result['State']['Failed'])
        self.assertEqual(result['State']['Stage'], 4)
        self.assertEqual(result['Calls'][-1], 'compose stop --timeout 10 dictation whisper')

    def test_already_open_leaves_services_alone(self):
        result = self.run_worker('already-open')
        self.assertTrue(result['State']['AlreadyOpen'])
        self.assertTrue(result['State']['Done'])
        self.assertEqual(result['Calls'], [])
