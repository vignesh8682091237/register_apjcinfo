Expo React Native starter for APJC INFO TECH

Quick overview
- This is a minimal Expo app that fetches live registration data from your server `/api/registrations`.
- It stores the API key securely on device using `expo-secure-store` and supports polling every 30s.

Setup (recommended: use a separate terminal)
1. Install/create the Expo app (if you don't have an app yet):

   npx create-expo-app mobile

2. Replace the generated `App.js` with the `App.js` in this folder (or copy the file contents into your new project).
3. Install runtime deps inside the `mobile` folder:

   cd mobile
   npx expo install expo-secure-store

4. Start the app:

   npx expo start

Notes on `API_URL`
- By default `App.js` uses `API_URL = 'http://10.0.2.2:5000/api/registrations'` which works for Android emulators (maps to localhost).
- For a physical device, use your machine IP (e.g. `http://192.168.1.10:5000/api/registrations`) and ensure the server is reachable and using HTTP or HTTPS appropriately.

Building an APK
- EAS (recommended): follow Expo docs to configure `eas.json` and run `eas build -p android --profile production`.
- Classic (managed): `expo build:android` (deprecated on newer workflows).

Security
- Do NOT hardcode the API key in production. Use secure storage and user authentication / server-issued short-lived tokens.

What this scaffold includes
- `App.js`: minimal UI to set API key, view registrations, and toggle polling.

If you want, I can:
- Create the full Expo project files here (package.json, app.json) and configure EAS settings.
- Add secure-key entry UI improvements or push-notification examples.
