<# : launcher_batch_wrapper
@echo off
setlocal
powershell -ExecutionPolicy Bypass -NoProfile -Command "Invoke-Expression ([System.IO.File]::ReadAllText('%~f0'))"
exit /b %errorlevel%
#>

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

[System.Windows.Forms.Application]::EnableVisualStyles()

# 1. Mutex: Protección contra abrir 6 veces seguidas la aplicación
$mutexName = "ComparadorPreciosSingleInstanceMutex"
$createdNew = $false
$mutex = New-Object System.Threading.Mutex($true, $mutexName, [ref]$createdNew)

if (-not $createdNew) {
    [System.Windows.Forms.MessageBox]::Show(
        "La aplicación ya se está ejecutando o iniciando en su equipo.`nPor favor revise su navegador web.",
        "Comparador de Listas de Precios",
        [System.Windows.Forms.MessageBoxButtons]::OK,
        [System.Windows.Forms.MessageBoxIcon]::Information
    )
    Start-Process "http://127.0.0.1:8000"
    exit 0
}

$appDir = "$env:LOCALAPPDATA\ComparadorPrecios"
$exePath = "$appDir\ComparadorPrecios.exe"
$githubUrl = "https://github.com/Viega095/Listas-Precios/releases/latest/download/ComparadorPrecios.exe"

if (-not (Test-Path $appDir)) {
    New-Item -ItemType Directory -Path $appDir -Force | Out-Null
}

# 2. Ventana gráfica de instalación / carga
$form = New-Object System.Windows.Forms.Form
$form.Text = "Comparador de Listas de Precios"
$form.Size = New-Object System.Drawing.Size(460, 210)
$form.StartPosition = "CenterScreen"
$form.FormBorderStyle = "FixedDialog"
$form.MaximizeBox = $false
$form.MinimizeBox = $false
$form.BackColor = [System.Drawing.Color]::FromArgb(248, 250, 252)

$lblTitle = New-Object System.Windows.Forms.Label
$lblTitle.Text = "Comparador de Listas de Precios"
$lblTitle.Font = New-Object System.Drawing.Font("Segoe UI", 12, [System.Drawing.FontStyle]::Bold)
$lblTitle.ForeColor = [System.Drawing.Color]::FromArgb(15, 23, 42)
$lblTitle.Location = New-Object System.Drawing.Point(24, 20)
$lblTitle.Size = New-Object System.Drawing.Size(400, 26)
$form.Controls.Add($lblTitle)

$lblStatus = New-Object System.Windows.Forms.Label
$lblStatus.Text = "Verificando instalación y componentes..."
$lblStatus.Font = New-Object System.Drawing.Font("Segoe UI", 9)
$lblStatus.ForeColor = [System.Drawing.Color]::FromArgb(71, 85, 105)
$lblStatus.Location = New-Object System.Drawing.Point(24, 50)
$lblStatus.Size = New-Object System.Drawing.Size(400, 20)
$form.Controls.Add($lblStatus)

$pb = New-Object System.Windows.Forms.ProgressBar
$pb.Location = New-Object System.Drawing.Point(24, 78)
$pb.Size = New-Object System.Drawing.Size(395, 22)
$pb.Minimum = 0
$pb.Maximum = 100
$pb.Value = 15
$form.Controls.Add($pb)

$lblDetail = New-Object System.Windows.Forms.Label
$lblDetail.Text = "Por favor espere un momento..."
$lblDetail.Font = New-Object System.Drawing.Font("Segoe UI", 8)
$lblDetail.ForeColor = [System.Drawing.Color]::FromArgb(148, 163, 184)
$lblDetail.Location = New-Object System.Drawing.Point(24, 108)
$lblDetail.Size = New-Object System.Drawing.Size(400, 18)
$form.Controls.Add($lblDetail)

$timer = New-Object System.Windows.Forms.Timer
$timer.Interval = 100

$timer.Add_Tick({
    $timer.Stop()
    
    # Comprobar si existe el ejecutable
    if (-not (Test-Path $exePath)) {
        $lblStatus.Text = "Descargando la aplicación desde GitHub..."
        $lblDetail.Text = "Descargando ComparadorPrecios.exe (Releases)..."
        $pb.Style = "Marquee"
        $pb.MarqueeAnimationSpeed = 30
        $form.Refresh()
        
        try {
            [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
            $client = New-Object Net.WebClient
            $client.DownloadFile($githubUrl, $exePath)
            $pb.Style = "Blocks"
            $pb.Value = 85
            $lblStatus.Text = "Descarga completada con éxito."
            $form.Refresh()
        } catch {
            $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
            $localExe = Join-Path $scriptDir "dist\ComparadorPrecios.exe"
            $localExe2 = Join-Path $scriptDir "ComparadorPrecios.exe"
            if (Test-Path $localExe) {
                Copy-Item $localExe $exePath -Force
            } elseif (Test-Path $localExe2) {
                Copy-Item $localExe2 $exePath -Force
            } else {
                [System.Windows.Forms.MessageBox]::Show("No se pudo descargar la aplicación desde GitHub.`nVerifique su conexión a internet.", "Error de Descarga", [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Error)
                $form.Close()
                return
            }
        }
    }
    
    # Crear acceso directo en el Escritorio
    $desktopPath = [Environment]::GetFolderPath("Desktop")
    $shortcutPath = Join-Path $desktopPath "Comparador de Precios.lnk"
    if (-not (Test-Path $shortcutPath)) {
        $wsh = New-Object -ComObject WScript.Shell
        $sc = $wsh.CreateShortcut($shortcutPath)
        $sc.TargetPath = $exePath
        $sc.WorkingDirectory = $appDir
        $sc.Description = "Comparador de Listas de Precios"
        $sc.Save()
    }
    
    # Iniciar la aplicación
    $pb.Value = 100
    $lblStatus.Text = "Iniciando servidor y abriendo navegador..."
    $lblDetail.Text = "La ventana se abrirá en unos segundos..."
    $form.Refresh()
    Start-Sleep -Milliseconds 800
    
    Start-Process -FilePath $exePath
    Start-Sleep -Milliseconds 1200
    $form.Close()
})

$form.Add_Shown({
    $timer.Start()
})

[System.Windows.Forms.Application]::Run($form)
