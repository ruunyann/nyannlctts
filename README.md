# PSO2NGS LCT — Live Chat Translator

แปลข้อความ Chat ใน PSO2 New Genesis แบบ Real-time (EN ↔ JP ↔ TH)

---

## สำหรับผู้ใช้ทั่วไป (ไม่ต้อง install อะไร)

1. ไปที่ **[Releases](../../releases/latest)**
2. โหลด `PSO2NGS_LCT_vX.X.X.zip`
3. แตก ZIP → ดับเบิลคลิก **`PSO2NGS LCT.exe`**

---

## สำหรับนักพัฒนา (Build เอง)

### ความต้องการ
- [Python 3.10+](https://www.python.org/downloads/)
- [Node.js 18+](https://nodejs.org/)
- Windows 10/11 x64

### วิธี Build
```
ดับเบิลคลิก build.bat
```
ไฟล์ ZIP จะอยู่ที่ `release/`

### Build แยกทีละขั้น
```bat
# 1. ติดตั้ง dependencies
pip install flask flask-socketio pyinstaller
npm install

# 2. Build Python → EXE (ใช้ .spec)
pyinstaller PSO2NGS_LCT_server.spec --distpath server_files

# 3. Build Electron
npm run dist
```

---

## โครงสร้างโฟลเดอร์

```
PSO2NGS_LCT/
├── main.js                      ← Electron main process
├── preload.js                   ← Electron preload (electronAPI)
├── package.json
├── PSO2NGS_LCT_server.spec      ← PyInstaller spec (hiddenimports, icon)
├── server.ico                   ← Icon สำหรับ EXE และ System Tray
├── build.bat                    ← Build script (Windows)
├── app_files/
│   └── PSO2NGS_LCT.html         ← Frontend UI
└── server_files/
    ├── PSO2NGS_LCT_server.py    ← Flask backend (source)
    └── PSO2NGS_LCT_server.exe   ← (หลัง build)
```

---

## หมายเหตุ

- กด **X** ที่หน้าต่าง → App ยังทำงานอยู่ใน **System Tray**
- กด **Quit** ใน System Tray → ปิด App และ Server พร้อมกัน

---

## License
AGPL-3.0
