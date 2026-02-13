@echo off
set REPO_URL=https://github.com/Ganesh-36-12/AlgoTrading/archive/refs/heads/main.zip
set PROJECT_NAME=REPO_NAME

echo ===============================
echo Updating project from GitHub
echo ===============================

:: Clean old files
if exist %PROJECT_NAME% (
    echo Removing old project...
    rmdir /s /q %PROJECT_NAME%
)

if exist repo.zip del repo.zip

:: Download repo
echo Downloading latest code...
powershell -Command "Invoke-WebRequest %REPO_URL% -OutFile repo.zip"

:: Unzip
echo Extracting files...
powershell -Command "Expand-Archive -Force repo.zip temp"

:: Rename folder
move temp\%PROJECT_NAME%-main %PROJECT_NAME%

:: Cleanup
rmdir /s /q temp
del repo.zip

:: Install dependencies
echo Installing required packages...
python -m pip install --upgrade pip
pip install -r %PROJECT_NAME%\requirements.txt

echo ===============================
echo Setup complete!
echo ===============================
pause