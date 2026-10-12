@echo off
title Gesture Mouse Control
cd /d "%~dp0release\GestureMouseControl"
echo Starting Gesture Mouse Control System...
start "" "%~dp0release\GestureMouseControl\GestureMouseControl.exe" %*
