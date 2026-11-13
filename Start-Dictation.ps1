# Render immediately; startup runs on a separate runspace.
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName PresentationFramework, PresentationCore, WindowsBase
[xml]$markup = @"
<Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation" xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml" Title="Starting SimpleWhisper" Width="472" Height="480" WindowStartupLocation="CenterScreen" ResizeMode="NoResize" WindowStyle="None" AllowsTransparency="True" Background="Transparent">
 <Border Background="#181B20" BorderBrush="#343B46" BorderThickness="1" CornerRadius="16" Padding="28">
  <Grid>
   <Grid.RowDefinitions><RowDefinition Height="Auto"/><RowDefinition Height="Auto"/><RowDefinition Height="Auto"/><RowDefinition Height="*"/><RowDefinition Height="Auto"/></Grid.RowDefinitions>
   <StackPanel>
    <TextBlock Text="S I M P L E W H I S P E R" Foreground="#A9B8CC" FontSize="11" FontWeight="SemiBold"/>
    <TextBlock x:Name="Heading" Text="Getting ready" Foreground="#F1F4F8" FontFamily="Segoe UI" FontSize="27" FontWeight="SemiBold" Margin="0,12,0,5"/>
    <TextBlock Text="Your voice. Your computer." Foreground="#929DAD" FontSize="13"/>
   </StackPanel>
   <StackPanel Grid.Row="1" Margin="0,24,0,18" x:Name="Checklist"/>
   <ProgressBar Grid.Row="2" x:Name="Progress" Height="3" Background="#2B313B" Foreground="#83B9D9" BorderThickness="0" IsIndeterminate="True"/>
   <StackPanel Grid.Row="3" Margin="0,14,0,0">
    <TextBlock x:Name="Status" Text="Preparing startup..." Foreground="#C5CEDB" FontSize="12" TextWrapping="Wrap"/>
    <TextBox x:Name="Details" Visibility="Collapsed" Margin="0,10,0,0" Height="108" IsReadOnly="True" TextWrapping="Wrap" VerticalScrollBarVisibility="Auto" Background="#111419" Foreground="#D8DEE8" BorderBrush="#343B46" Padding="8" FontSize="11"/>
   </StackPanel>
   <Grid Grid.Row="4" Margin="0,16,0,0">
    <TextBlock x:Name="Footer" Text="LOCAL SPEECH / MICROPHONE OFF" Foreground="#788596" FontSize="10" VerticalAlignment="Center"/>
    <Button x:Name="CloseButton" Content="Close" Visibility="Collapsed" HorizontalAlignment="Right" Padding="18,6" Background="#303B49" Foreground="#F1F4F8" BorderThickness="0"/>
   </Grid>
  </Grid>
 </Border>
</Window>
"@
$window = [Windows.Markup.XamlReader]::Load((New-Object Xml.XmlNodeReader $markup))
$heading = $window.FindName('Heading'); $status = $window.FindName('Status')
$progress = $window.FindName('Progress'); $details = $window.FindName('Details')
$footer = $window.FindName('Footer'); $close = $window.FindName('CloseButton')
$rows = @()
foreach ($label in @('App & configuration', 'Docker Desktop', 'Speech model', 'Dictation service', 'Microphone toolbar')) {
    $row = New-Object Windows.Controls.StackPanel
    $row.Orientation = 'Horizontal'; $row.Margin = '0,0,0,13'
    $badge = New-Object Windows.Controls.TextBlock
    $badge.Width = 28; $badge.FontSize = 15; $badge.Text = [char]0x25CB
    $text = New-Object Windows.Controls.TextBlock
    $text.Text = $label; $text.FontSize = 14
    $row.Children.Add($badge) | Out-Null; $row.Children.Add($text) | Out-Null
    $window.FindName('Checklist').Children.Add($row) | Out-Null
    $rows += ,@($badge, $text)
}
$state = [hashtable]::Synchronized(@{Stage=0; Message='Preparing startup...'; Done=$false; Failed=$false; Detail=''; AlreadyOpen=$false})
$runner = [PowerShell]::Create()
$null = $runner.AddScript('param($path, $state) & $path -State $state').AddArgument((Join-Path $PSScriptRoot 'Start-DictationWorker.ps1')).AddArgument($state)
$started = [Diagnostics.Stopwatch]::StartNew()
$completionSeen = $null
$timer = New-Object Windows.Threading.DispatcherTimer
$timer.Interval = [TimeSpan]::FromMilliseconds(100)
$timer.Add_Tick({
    if ($task.IsCompleted -and !$state.Done) {
        $state.Failed = $true; $state.Done = $true
        $state.Detail = ($runner.Streams.Error | Out-String)
        $state.Message = 'Startup needs attention'
    }
    $status.Text = $state.Message
    for ($i=0; $i -lt $rows.Count; $i++) {
        $color = '#778394'; $symbol = [char]0x25CB
        if (!$state.AlreadyOpen -and ($i -lt $state.Stage -or ($state.Done -and !$state.Failed))) { $color = '#8FCAB0'; $symbol = [char]0x2713 }
        elseif ($i -eq $state.Stage) {
            $color = '#A8D4EE'; $symbol = [char]0x25CF
            if ($state.Failed) { $color = '#E4A2A2'; $symbol = '!' }
        }
        $rows[$i][0].Text = [string]$symbol
        $rows[$i][0].Foreground = $color; $rows[$i][1].Foreground = $color
    }
    $footer.Text = 'LOCAL SPEECH / ' + [int]$started.Elapsed.TotalSeconds + 's'
    if ($state.Done) {
        $progress.IsIndeterminate = $false
        if ($state.Failed) {
            $heading.Text = 'Startup needs attention'
            $window.Height = 600
            $progress.Foreground = '#E4A2A2'; $progress.Value = 100
            $details.Text = $state.Detail; $details.Visibility = 'Visible'
            $close.Visibility = 'Visible'; $footer.Text = 'MICROPHONE OFF'
        } else {
            $heading.Text = 'Ready to dictate'; $progress.Value = 100
            if ($state.AlreadyOpen) { $heading.Text = 'Already open' }
            if (!$script:completionSeen) { $script:completionSeen = [DateTime]::UtcNow }
            if (([DateTime]::UtcNow - $script:completionSeen).TotalSeconds -ge 1.5) { $window.Close() }
        }
    }
})
$window.Add_MouseLeftButtonDown({ if ($_.ChangedButton -eq 'Left') { $window.DragMove() } })
$window.Add_Closing({ if (!$state.Done) { $_.Cancel = $true } })
$close.Add_Click({ $window.Close() })
$window.Add_ContentRendered({ $script:task = $runner.BeginInvoke(); $timer.Start() })
try { $null = $window.ShowDialog() }
finally {
    $timer.Stop()
    if ($task) { $null = $runner.EndInvoke($task) }
    $runner.Dispose()
}
