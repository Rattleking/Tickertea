<#
  db-setup.ps1 — one-shot local database setup against native PostgreSQL (no Docker).

  Steps:
    1. Bootstrap roles + database (db/local_setup.sql) as the postgres SUPERUSER.
    2. Apply migrations (db/migrations/*.sql) to the tickertea DB as tickertea_admin.
    3. Load seed data (db/seed/*.sql).
    4. Print a verification summary.

  RUN THIS IN YOUR OWN TERMINAL (it prompts for the postgres password securely):
    powershell -ExecutionPolicy Bypass -File scripts/db-setup.ps1

  The superuser password is read via a hidden prompt (or $env:PGPASSWORD if already set)
  and is never written to disk or echoed. The tickertea_* role password is 'tickertea'
  (matches .env.example); change it for non-local use.
#>
[CmdletBinding()]
param(
  [string]$Superuser = "postgres",
  [string]$DbHost    = "localhost",
  [int]$Port         = 5432,
  [string]$Database  = "tickertea"
)

$ErrorActionPreference = "Stop"
$env:PGCLIENTENCODING  = "UTF8"

# Locate psql (newest PostgreSQL install).
$psql = Get-ChildItem 'C:\Program Files\PostgreSQL\*\bin\psql.exe' -ErrorAction SilentlyContinue |
        Sort-Object FullName -Descending | Select-Object -First 1 -ExpandProperty FullName
if (-not $psql) { throw "psql.exe not found under C:\Program Files\PostgreSQL" }
Write-Host "Using $psql"

$repoRoot = Split-Path -Parent $PSScriptRoot

function Invoke-Psql {
  param([string]$User, [string]$Db, [string]$Password, [string]$File, [string]$Sql)
  $env:PGPASSWORD = $Password
  $common = @("-v","ON_ERROR_STOP=1","-U",$User,"-h",$DbHost,"-p",$Port,"-d",$Db)
  if ($File) { & $psql @common -f $File } else { & $psql @common -c $Sql }
  if ($LASTEXITCODE -ne 0) { throw "psql failed (exit $LASTEXITCODE) on $(if($File){$File}else{$Sql})" }
}

# --- Superuser password (secure prompt, or reuse $env:PGPASSWORD) -------------------
if ($env:PGPASSWORD) {
  $superPw = $env:PGPASSWORD
  Write-Host "Using postgres password from `$env:PGPASSWORD"
} else {
  $secure  = Read-Host "Password for PostgreSQL superuser '$Superuser'" -AsSecureString
  $superPw = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
              [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure))
}

# --- 1. Bootstrap roles + database --------------------------------------------------
Write-Host "`n[1/3] Bootstrapping roles + database..."
Invoke-Psql -User $Superuser -Db "postgres" -Password $superPw -File "$repoRoot\db\local_setup.sql"

# --- 2. Migrations (as tickertea_admin) ----------------------------------------------
Write-Host "`n[2/3] Applying migrations..."
$adminPw = "tickertea"
Get-ChildItem "$repoRoot\db\migrations\*.sql" | Sort-Object Name | ForEach-Object {
  Write-Host ("  - " + $_.Name)
  Invoke-Psql -User "tickertea_admin" -Db $Database -Password $adminPw -File $_.FullName
}

# --- 3. Seed ------------------------------------------------------------------------
Write-Host "`n[3/3] Loading seed data..."
Get-ChildItem "$repoRoot\db\seed\*.sql" | Sort-Object Name | ForEach-Object {
  Write-Host ("  - " + $_.Name)
  Invoke-Psql -User "tickertea_admin" -Db $Database -Password $adminPw -File $_.FullName
}

# --- Verify -------------------------------------------------------------------------
Write-Host "`nVerification:"
$verify = @"
SELECT 'companies'   AS entity, count(*) FROM company
UNION ALL SELECT 'categories', count(*) FROM signal_category
UNION ALL SELECT 'sources',    count(*) FROM source
UNION ALL SELECT 'signals',    count(*) FROM signal
UNION ALL SELECT 'evidence',   count(*) FROM signal_evidence
UNION ALL SELECT 'scores',     count(*) FROM signal_score
ORDER BY entity;
"@
Invoke-Psql -User "tickertea_admin" -Db $Database -Password $adminPw -Sql $verify

$env:PGPASSWORD = $null
Write-Host "`nDone. App connection string:"
Write-Host "  postgres://tickertea_app:tickertea@${DbHost}:${Port}/${Database}"
