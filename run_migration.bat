@echo off
echo ========================================
echo    DATABASE MIGRATION FOR MOMCONNECT
echo ========================================
echo.

echo [1] Kiem tra database hien tai
echo [2] Tao bang moi (don gian nhat)
echo [3] Fix migration (SQLAlchemy 2.0+)
echo [4] Thoat
echo.

set /p choice="Chon mot tuy chon (1-4): "

if "%choice%"=="1" (
    echo.
    echo Dang kiem tra database...
    python check_database.py
    pause
) else if "%choice%"=="2" (
    echo.
    echo Dang tao bang moi...
    python create_tables.py
    pause
) else if "%choice%"=="3" (
    echo.
    echo Dang fix migration...
    python fix_migration.py
    pause
) else if "%choice%"=="4" (
    echo Thoat...
    exit
) else (
    echo Lua chon khong hop le!
    pause
)