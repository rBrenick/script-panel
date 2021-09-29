
:: script_panel is determined by the current folder name
for %%I in (.) do set script_panel=%%~nxI
SET CLEAN_script_panel=%script_panel:-=_%

:: Check if modules folder exists
if not exist %UserProfile%\Documents\maya\modules mkdir %UserProfile%\Documents\maya\modules

:: Delete .mod file if it already exists
if exist %UserProfile%\Documents\maya\modules\%script_panel%.mod del %UserProfile%\Documents\maya\modules\%script_panel%.mod

:: Create file with contents in users maya/modules folder
(echo|set /p=+ %script_panel% 1.0 %CD%\_install_ & echo; & echo icons: ..\%CLEAN_script_panel%\icons)>%UserProfile%\Documents\maya\modules\%script_panel%.mod

:: end print
echo .mod file created at %UserProfile%\Documents\maya\modules\%script_panel%.mod


