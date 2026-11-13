# Reproducible vector artwork, supersampled to PNG. Runtime needs only Tk.
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing
$destination = Join-Path (Split-Path $PSScriptRoot) 'ui_assets'
New-Item -ItemType Directory -Force $destination | Out-Null
function Brush($color) { New-Object Drawing.SolidBrush([Drawing.ColorTranslator]::FromHtml($color)) }
function Pen($color, $width) {
    $pen = New-Object Drawing.Pen([Drawing.ColorTranslator]::FromHtml($color)), $width
    $pen.StartCap = 'Round'; $pen.EndCap = 'Round'
    return $pen
}
function Pill($g, $color, [single]$x, [single]$y, [single]$w, [single]$h) {
    $b = Brush $color
    if ($w -ge $h) {
        $g.FillEllipse($b, $x, $y, $h, $h)
        $g.FillEllipse($b, ($x+$w-$h), $y, $h, $h)
        $g.FillRectangle($b, ($x+$h/2), $y, ($w-$h), $h)
    } else {
        $g.FillEllipse($b, $x, $y, $w, $w)
        $g.FillEllipse($b, $x, ($y+$h-$w), $w, $w)
        $g.FillRectangle($b, $x, ($y+$w/2), $w, ($h-$w))
    }
    $b.Dispose()
}
foreach ($kind in @('mic', 'toggle', 'gear')) {
 foreach ($on in @($false, $true)) {
  if ($kind -eq 'gear' -and $on) { continue }
  foreach ($hover in @($false, $true)) {
    $w = 46; $h = 46
    if ($kind -eq 'toggle') { $w=48; $h=28 }
    if ($kind -eq 'gear') { $w=34; $h=34 }
    $bitmap = New-Object Drawing.Bitmap ($w*4), ($h*4)
    $g = [Drawing.Graphics]::FromImage($bitmap)
    $g.SmoothingMode = 'AntiAlias'; $g.ScaleTransform(4,4)
    if ($kind -eq 'mic') {
        $fill = '#30252D'; $ring='#60404B'; $ink='#E9A3AE'
        if ($on) { $fill='#203A35'; $ring='#3B7763'; $ink='#A6E5C8' }
        if ($hover) { if ($on) { $fill='#294B41' } else { $fill='#42303A' } }
        $b=Brush $fill; $g.FillEllipse($b,1,1,44,44); $b.Dispose()
        $p=Pen $ring 1; $g.DrawEllipse($p,1.5,1.5,43,43); $p.Dispose()
        Pill $g $ink 19 10 8 18
        $p=Pen $ink 1.8; $g.DrawArc($p,14,17,18,17,0,180)
        $g.DrawLine($p,23,34,23,38); $g.DrawLine($p,18,38,28,38); $p.Dispose()
        $p=Pen $ring 0.7; $g.DrawArc($p,4,4,38,38,210,85); $p.Dispose()
    } elseif ($kind -eq 'toggle') {
        $fill='#2C333E'; if ($on) { $fill='#40657B' }
        if ($hover) { if ($on) { $fill='#4C7993' } else { $fill='#3B4654' } }
        Pill $g $fill 1 2 46 24
        $x=4; if ($on) { $x=24 }
        $b=Brush '#18232D'; $g.FillEllipse($b,$x,5,20,20); $b.Dispose()
        $b=Brush '#E5EEF5'; $g.FillEllipse($b,$x,4,20,20); $b.Dispose()
        $p=Pen '#FFFFFF' 1; $g.DrawArc($p,($x+1),5,18,18,200,110); $p.Dispose()
        if ($on) {
            $p=Pen '#A7CDE0' 1.4; $g.DrawLine($p,10,14,12,16); $g.DrawLine($p,12,16,16,11); $p.Dispose()
        }
    } else {
        $b=Brush $(if ($hover) {'#303B49'} else {'#20262F'})
        $g.FillEllipse($b,0,0,34,34); $b.Dispose()
        $p=Pen '#AABACC' 1.6
        $points = @()
        for ($i=0; $i -lt 48; $i++) {
            $angle=$i*[Math]::PI/24; $radius=8.5
            if (($i % 6) -in @(1,2,3)) { $radius=10.5 }
            $points += [Drawing.PointF]::new([single](17+$radius*[Math]::Cos($angle)), [single](17+$radius*[Math]::Sin($angle)))
        }
        $g.DrawPolygon($p,[Drawing.PointF[]]$points); $g.DrawEllipse($p,13.5,13.5,7,7); $p.Dispose()
    }
    $g.Dispose()
    $final = New-Object Drawing.Bitmap $w,$h
    $g=[Drawing.Graphics]::FromImage($final)
    $g.InterpolationMode='HighQualityBicubic'; $g.PixelOffsetMode='HighQuality'
    $g.DrawImage($bitmap,0,0,$w,$h); $g.Dispose(); $bitmap.Dispose()
    $name=$kind+'-'+$(if ($on) {'on'} else {'off'})+$(if ($hover) {'-hover'} else {''})+'.png'
    $final.Save((Join-Path $destination $name),[Drawing.Imaging.ImageFormat]::Png); $final.Dispose()
  }
 }
}
