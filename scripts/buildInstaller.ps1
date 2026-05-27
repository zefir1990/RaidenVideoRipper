$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path ".."

if (Test-Path "$ProjectRoot/build") {
    Remove-Item -Path "$ProjectRoot/build" -Recurse -Force
}
if (Test-Path "$ProjectRoot/dist") {
    Remove-Item -Path "$ProjectRoot/dist" -Recurse -Force
}

if (Test-Path "build") {
    Remove-Item -Path "build" -Recurse -Force
}
if (Test-Path "dist") {
    Remove-Item -Path "dist" -Recurse -Force
}

Write-Output "Running PyInstaller..."
& python -m PyInstaller "$ProjectRoot/main.spec" --distpath "$ProjectRoot/dist" --workpath "$ProjectRoot/build"
if ($LASTEXITCODE -ne 0) {
    Write-Error "PyInstaller build failed."
}

$IsccPaths = @(
    "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
    "C:\Program Files\Inno Setup 6\ISCC.exe",
    "ISCC.exe"
)

$IsccPath = $null
foreach ($path in $IsccPaths) {
    if ($path -eq "ISCC.exe") {
        $found = Get-Command "ISCC.exe" -ErrorAction SilentlyContinue
        if ($found) {
            $IsccPath = $found.Source
            break
        }
    } elseif (Test-Path $path) {
        $IsccPath = $path
        break
    }
}

if ($null -eq $IsccPath) {
    Write-Error "Inno Setup compiler (ISCC.exe) not found. Please install Inno Setup 6."
}

Write-Output "Using ISCC path: $IsccPath"
Write-Output "Compiling installer..."
& $IsccPath "$ProjectRoot/installer/config.iss"

Write-Output "Installer build complete!"
