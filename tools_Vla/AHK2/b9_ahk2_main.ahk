#Requires AutoHotkey v2.0

TraySetIcon A_ScriptDir "\P-icon.ico"

; ; Broader context: Explorer + classic dialogs (add more if needed)
; #HotIf WinActive("ahk_exe TOTALCMD64.EXE") || WinActive("ahk_exe explorer.exe") || WinActive("ahk_class #32770") || WinActive("ahk_class OperationStatusWindow")  ; Covers some modern dialogs

; *Shift::
; {
;     static lastTime := 0
;     static isHeld := false
;     currentTime := A_TickCount

;     ; Ignore repeats while key is held down
;     if isHeld
;         return
    
;     isHeld := true
;     KeyWait "Shift"  ; Wait for Shift to be released
;     isHeld := false

;     if (GetKeyState("LCtrl", "P") || GetKeyState("RCtrl", "P"))
;     {
;         if (lastTime && (currentTime - lastTime < 400))
;         {
;             Send "{Backspace}" 
;             ; Send "!{up}" 
;             lastTime := 0  ; Reset to avoid triples
;             return
;         }
;         lastTime := currentTime  ; Record first tap
;     }
;     else
;     {
;         lastTime := 0  ; Reset if no Ctrl
;     }
; }

; #HotIf
; --- Custom hotkeys ---
; Ctrl+Win+F11 — types 'basiTainata'
^#F11:: {
    Send("{Raw}basiTainata")
}
