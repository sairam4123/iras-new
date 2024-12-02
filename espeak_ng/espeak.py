import subprocess
ESPEAK_EXE = r"C:\Program Files\eSpeak NG\espeak-ng.exe"

class Speaker:
    def __init__(self, rate: int = 175, pitch: int = 50, amplitude: int = 100, ssml: bool = False) -> None:
        self.rate = rate
        self.pitch = pitch
        self.amplitude = amplitude
        self.ssml = ssml
        self.text = ""
    
    def speak(self, text: str):
        self.text += text
        return self

    def save_wav(self, path: str, reset: bool = True):
        self._run(path)
        if reset:
            self.text = ""
    
    def _run(self, path):
        subprocess.run([ESPEAK_EXE, self.text, f'-w {path}', f'-s {self.rate}', f'-p {self.pitch}', f'-a {self.amplitude}', '-ven-in'] + (['-m'] if self.ssml else []))
