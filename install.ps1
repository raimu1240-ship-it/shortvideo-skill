# shortvideo-skill Windows インストーラ
#
# 要件: symlink 作成のため以下のいずれかが必要
#   方法 A (推奨): Windows の「開発者モード」を ON にする
#   方法 B: PowerShell を管理者として実行
#
# symlink 不可の場合は自動でファイルコピーに切り替わる
# (コピー運用時は git pull 後に install.ps1 を再実行する)

$ErrorActionPreference = "Stop"

$repoDir   = Split-Path -Parent $MyInvocation.MyCommand.Path
$claudeDir = "$env:USERPROFILE\.claude"
$skillDir  = "$claudeDir\skills"
$agentDir  = "$claudeDir\agents"
$cmdDir    = "$claudeDir\commands"

New-Item -ItemType Directory -Force -Path $skillDir, $agentDir, $cmdDir | Out-Null

function Install-Link {
    param([string]$Source, [string]$Target)
    if (Test-Path $Target) {
        Remove-Item -Recurse -Force $Target
    }
    try {
        New-Item -ItemType SymbolicLink -Path $Target -Target $Source -ErrorAction Stop | Out-Null
        Write-Host "  linked: $Target"
    } catch {
        Write-Host "  symlink 不可 (管理者権限 or 開発者モードが必要)。コピーで代替します" -ForegroundColor Yellow
        if ((Get-Item $Source).PSIsContainer) {
            Copy-Item -Recurse $Source $Target
        } else {
            Copy-Item $Source $Target
        }
        Write-Host "  copied: $Target"
    }
}

Write-Host "shortvideo-skill をインストール中..."
foreach ($s in "shortvideo-planner", "shortvideo-generator", "shortvideo-reviewer") {
    Install-Link "$repoDir\.claude\skills\$s" "$skillDir\$s"
}
# Agents (planner / generator / reviewer の 3 つを subagent として登録)
foreach ($a in "shortvideo-planner", "shortvideo-generator", "shortvideo-reviewer") {
    Install-Link "$repoDir\.claude\agents\$a.md" "$agentDir\$a.md"
}
Install-Link "$repoDir\.claude\commands\shortvideo-loop.md" "$cmdDir\shortvideo-loop.md"

Write-Host ""
Write-Host "依存コマンドの確認:"
$missing = $false

function Check-Cmd {
    param([string]$Name)
    if (Get-Command $Name -ErrorAction SilentlyContinue) {
        Write-Host "  OK    $Name"
        return $true
    } else {
        Write-Host "  MISS  $Name" -ForegroundColor Red
        return $false
    }
}

# python は python3 か python のどちらかが入っていれば OK
$hasPython = $false
foreach ($p in "python", "python3") {
    if (Get-Command $p -ErrorAction SilentlyContinue) {
        Write-Host "  OK    $p"
        $hasPython = $true
        $pythonCmd = $p
        break
    }
}
if (-not $hasPython) {
    Write-Host "  MISS  python (python or python3 が必要)" -ForegroundColor Red
    $missing = $true
}

if (-not (Check-Cmd "ffmpeg"))  { $missing = $true }
if (-not (Check-Cmd "ffprobe")) { $missing = $true }

# Pillow チェック (Python が入っている時のみ)
if ($hasPython) {
    & $pythonCmd -c "import PIL" 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  OK    Pillow"
    } else {
        Write-Host "  MISS  Pillow" -ForegroundColor Red
        $missing = $true
    }
}

if ($missing) {
    Write-Host ""
    Write-Host "不足コマンドのインストール例:" -ForegroundColor Yellow
    Write-Host "  winget install Python.Python.3.12"
    Write-Host "  winget install Gyan.FFmpeg"
    Write-Host "  pip install Pillow"
    Write-Host ""
    Write-Host "インストール後、新しい PowerShell ウィンドウを開いて install.ps1 を再実行してください。"
    exit 1
}

# .env 自動作成
if (-not (Test-Path "$repoDir\.env")) {
    Copy-Item "$repoDir\.env.example" "$repoDir\.env"
    Write-Host ""
    Write-Host ".env を作成しました。ElevenLabs を使う場合は ELEVENLABS_API_KEY を設定してください。"
    Write-Host "未設定なら Windows 内蔵 TTS (System.Speech.Synthesizer) にフォールバックします。"
}

Write-Host ""
Write-Host "インストール完了。Claude Code で次のコマンドを試してください:" -ForegroundColor Green
Write-Host "  cd $repoDir"
Write-Host "  claude"
Write-Host "  /shortvideo-loop my-first-project"
