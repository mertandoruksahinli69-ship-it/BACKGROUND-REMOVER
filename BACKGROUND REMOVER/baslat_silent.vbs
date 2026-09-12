' Arka Plan Kaldırıcı — tamamen sessiz başlatıcı (hiçbir pencere/terminal açılmaz)
Dim sh, fso, dirPath
Set sh = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
dirPath = fso.GetParentFolderName(WScript.ScriptFullName)
sh.CurrentDirectory = dirPath
sh.Run "pythonw """ & dirPath & "\background_remover.py""", 0, False
