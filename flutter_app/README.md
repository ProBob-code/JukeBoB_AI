## JukeBoB Flutter App

This Flutter app mirrors the existing web app's sections and logic:
- Jukebox (host/join, queue, requests, tips UI)
- Games (Tic Tac Toe with realtime updates)
- AI DJ (basic UI stub)

It connects to your existing FastAPI backend.

### Prerequisites
- Flutter SDK installed (`flutter --version`)
- Backend running locally on `http://localhost:5000` (already working in this repo)

### One-time setup
1. Open a terminal in this folder:
   - `cd flutter_app`
2. Initialize platform folders (Android/iOS/web/macOS/windows/linux) using Flutter:
   - `flutter create .`
3. Get dependencies:
   - `flutter pub get`

### Run
- Mobile (Android): `flutter run -d android`
- Web: `flutter run -d chrome --web-renderer html`

### Configure backend URL
- By default the app points to `http://localhost:5000`.
- Override at build time:
  - `flutter run -d chrome --dart-define=BACKEND_BASE_URL=http://localhost:5000`
  - `flutter run -d android --dart-define=BACKEND_BASE_URL=http://10.0.2.2:5000` (Android emulator)

Tip: For Android emulator, use `http://10.0.2.2:5000` to access the host machine.


