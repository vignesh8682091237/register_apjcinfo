Secure storage notes

This scaffold uses `expo-secure-store` to persist the API key on device. In production consider:

- Using a server-side auth flow where the app authenticates users and the server issues short-lived tokens (safer than shipping an admin key to devices).
- Storing tokens in `SecureStore` (Expo) or `react-native-keychain` (bare RN) and refreshing tokens when expired.
- Use HTTPS for all API calls.
