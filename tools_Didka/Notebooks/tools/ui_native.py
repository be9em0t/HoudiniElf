# tools/ui_native.py

import platform
import subprocess


def pick_file(filter="All files (*.*)|*.*"):
    system = platform.system()

    if system == "Darwin":  # macOS
        script = '''
        set theFile to choose file
        POSIX path of theFile
        '''
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True
        )
        return result.stdout.strip()

    elif system == "Windows":
        ps_script = fr'''
        Add-Type -AssemblyName System.Windows.Forms
        $ofd = New-Object System.Windows.Forms.OpenFileDialog
        $ofd.Filter = "{filter}"
        if ($ofd.ShowDialog() -eq "OK") {{ Write-Output $ofd.FileName }}
        '''
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_script],
            capture_output=True,
            text=True
        )
        return result.stdout.strip()

    else:
        raise NotImplementedError("Native file dialog not implemented for this OS")
