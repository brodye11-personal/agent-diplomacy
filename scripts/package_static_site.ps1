param(
    [Parameter(Mandatory = $true)]
    [string]$OutputPath
)

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot '..')
$siteRoot = Join-Path $repoRoot 'site'
$distRoot = Join-Path $siteRoot 'dist'
$resolvedOutput = [System.IO.Path]::GetFullPath($OutputPath)

if (Test-Path -LiteralPath $resolvedOutput) {
    throw "Refusing to overwrite existing archive: $resolvedOutput"
}

Push-Location -LiteralPath $siteRoot
try {
    npm run build
    if ($LASTEXITCODE -ne 0) { throw "Astro build failed with exit code $LASTEXITCODE" }
}
finally {
    Pop-Location
}

# Compress-Archive records Windows backslashes in ZIP entry names. Cloudflare's
# static uploader then cannot serve nested paths such as /_astro/*.css.
tar.exe -a -c -f $resolvedOutput -C $distRoot .
if ($LASTEXITCODE -ne 0) { throw "Archive creation failed with exit code $LASTEXITCODE" }

Add-Type -AssemblyName System.IO.Compression.FileSystem
$archive = [System.IO.Compression.ZipFile]::OpenRead($resolvedOutput)
try {
    $invalid = $archive.Entries | Where-Object { $_.FullName.Contains('\') }
    if ($invalid) { throw 'Archive contains Windows-style paths and is unsafe to upload.' }
    if (-not ($archive.Entries | Where-Object { $_.FullName -eq './index.html' -or $_.FullName -eq 'index.html' })) {
        throw 'Archive is missing its root index.html.'
    }
}
finally {
    $archive.Dispose()
}

Write-Output "Created Cloudflare-safe archive: $resolvedOutput"
