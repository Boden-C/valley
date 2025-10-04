#NoEnv  ; Recommended for performance and compatibility with future AutoHotkey releases.
; #Warn  ; Enable warnings to assist with detecting common errors.
SendMode Input  ; Recommended for new scripts due to its superior speed and reliability.
SetWorkingDir %A_ScriptDir%  ; Ensures a consistent starting directory.

F1::
    InputBox, nextCellKey, Next Cell Key, What key to press for next cell?, , 250, 150, , , , , Tab
    if (ErrorLevel) {
        return
    }
    if (StrLen(nextCellKey) > 1) {
        nextCellKey := "{" . nextCellKey . "}"
    }

    InputBox, nextPageKey, Next Page Key, What key to press for next page?, , 250, 150, , , , , PgDn
    if (ErrorLevel) {
        return
    }
    if (StrLen(nextPageKey) > 1) {
        nextPageKey := "{" . nextPageKey . "}"
    }

    FileRead, csv_content, macro.csv
    if (ErrorLevel) {
        MsgBox, Could not open macro.csv.
        return
    }

    Loop, parse, csv_content, `n, `r
    {
        if (A_Index = 1) ; Skip header row
            continue

        row := A_LoopField
        Loop, parse, row, CSV
        {
            text_to_send := A_LoopField
            Send, %text_to_send%

            next_index := A_Index + 1
            next_val := ""
            Loop, parse, row, CSV
            {
                if (A_Index = next_index) {
                    next_val := A_LoopField
                    break
                }
            }

            if next_val is integer
            {
                Loop, %next_val%
                {
                    Send, %nextCellKey%
                }
            } else {
                break ; Last item on the line
            }
        }
    }
return

