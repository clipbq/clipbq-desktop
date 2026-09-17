# ClipBQ
This app gives only you access to your clipboard, everywhere

# Requirements
- Desktop or Laptop
- Mobile phone (Android or iOS)

# 🍏 How to Install on macOS (Gatekeeper Bypass)
Because this app is built through an automated CI pipeline and is not digitally signed by Apple, macOS will block it by default. If you see a "damaged file" or "unverified developer" warning, follow these quick steps:

1. Unzip the download and drag clipBQ.app into your Applications folder.
2. Open your Mac's Terminal app (Press Cmd + Space, type "Terminal", and hit Enter).
3. Copy and paste the following command, then press Enter:
```bash
xattr -cr /Applications/clipBQ.app
```
4. Double-click the app to open it normally.