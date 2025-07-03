# Mobile Google OAuth Implementation Guide

## Overview

The Google OAuth implementation has been extended to support mobile applications. The original web-based implementation used redirects, which don't work well in mobile apps. The mobile implementation provides JSON-based endpoints that return authentication URLs and tokens.

## Key Differences Between Web and Mobile OAuth

### Web OAuth Flow (Original)
1. User clicks login → Redirects to Google OAuth
2. Google redirects back to `/callback` with authorization code
3. Server exchanges code for token and redirects to frontend with JWT
4. Frontend extracts JWT from URL parameters

### Mobile OAuth Flow (New)
1. Mobile app calls `/mobile/login` → Gets authorization URL
2. Mobile app opens URL in WebView/browser
3. Google redirects to `/mobile/callback` with authorization code
4. Server returns JSON response with JWT token
5. Mobile app receives JWT in JSON response

## New Mobile Endpoints

### 1. `/mobile/login` (GET)
**Purpose**: Generate Google OAuth authorization URL for mobile apps

**Response**:
```json
{
  "auth_url": "https://accounts.google.com/o/oauth2/auth?...",
  "message": "Use this URL to open Google OAuth in mobile browser or WebView"
}
```

**Mobile App Usage**:
```javascript
// React Native example
const response = await fetch('/api/auth/google/mobile/login');
const data = await response.json();
// Open data.auth_url in WebView or browser
```

### 2. `/mobile/callback` (GET)
**Purpose**: Handle OAuth callback and return JWT token as JSON

**Response**:
```json
{
  "success": true,
  "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "user": {
    "id": 123,
    "email": "user@example.com",
    "is_active": true
  },
  "message": "Authentication successful"
}
```

### 3. `/mobile/token` (POST)
**Purpose**: Exchange authorization code for JWT token (alternative flow)

**Request Body**:
```
code=authorization_code_here
```

**Response**:
```json
{
  "success": true,
  "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "user": {
    "id": 123,
    "email": "user@example.com",
    "is_active": true
  }
}
```

## Mobile App Implementation Examples

### React Native Example

```javascript
import { WebView } from 'react-native-webview';

const GoogleLogin = () => {
  const [authUrl, setAuthUrl] = useState(null);
  const [webViewVisible, setWebViewVisible] = useState(false);

  const initiateLogin = async () => {
    try {
      const response = await fetch('https://your-api.com/api/auth/google/mobile/login');
      const data = await response.json();
      setAuthUrl(data.auth_url);
      setWebViewVisible(true);
    } catch (error) {
      console.error('Login initiation failed:', error);
    }
  };

  const handleNavigationStateChange = (navState) => {
    // Check if the URL contains the callback
    if (navState.url.includes('/mobile/callback')) {
      // Extract the authorization code from URL
      const url = new URL(navState.url);
      const code = url.searchParams.get('code');
      
      if (code) {
        // Exchange code for token
        exchangeCodeForToken(code);
        setWebViewVisible(false);
      }
    }
  };

  const exchangeCodeForToken = async (code) => {
    try {
      const formData = new FormData();
      formData.append('code', code);
      
      const response = await fetch('https://your-api.com/api/auth/google/mobile/token', {
        method: 'POST',
        body: formData,
      });
      
      const data = await response.json();
      
      if (data.success) {
        // Store the JWT token
        await AsyncStorage.setItem('authToken', data.token);
        // Navigate to main app
        navigation.navigate('Main');
      }
    } catch (error) {
      console.error('Token exchange failed:', error);
    }
  };

  return (
    <View>
      <Button title="Login with Google" onPress={initiateLogin} />
      
      {webViewVisible && authUrl && (
        <WebView
          source={{ uri: authUrl }}
          onNavigationStateChange={handleNavigationStateChange}
          style={{ flex: 1 }}
        />
      )}
    </View>
  );
};
```

### Flutter Example

```dart
import 'package:webview_flutter/webview_flutter.dart';
import 'package:http/http.dart' as http;

class GoogleLogin extends StatefulWidget {
  @override
  _GoogleLoginState createState() => _GoogleLoginState();
}

class _GoogleLoginState extends State<GoogleLogin> {
  String? authUrl;
  bool showWebView = false;

  Future<void> initiateLogin() async {
    try {
      final response = await http.get(
        Uri.parse('https://your-api.com/api/auth/google/mobile/login'),
      );
      
      final data = jsonDecode(response.body);
      setState(() {
        authUrl = data['auth_url'];
        showWebView = true;
      });
    } catch (e) {
      print('Login initiation failed: $e');
    }
  }

  Future<void> exchangeCodeForToken(String code) async {
    try {
      final response = await http.post(
        Uri.parse('https://your-api.com/api/auth/google/mobile/token'),
        body: {'code': code},
      );
      
      final data = jsonDecode(response.body);
      
      if (data['success']) {
        // Store the JWT token
        await SharedPreferences.getInstance().then((prefs) {
          prefs.setString('authToken', data['token']);
        });
        // Navigate to main app
        Navigator.pushReplacementNamed(context, '/main');
      }
    } catch (e) {
      print('Token exchange failed: $e');
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: showWebView && authUrl != null
          ? WebView(
              initialUrl: authUrl,
              navigationDelegate: (NavigationRequest request) {
                if (request.url.contains('/mobile/callback')) {
                  final uri = Uri.parse(request.url);
                  final code = uri.queryParameters['code'];
                  
                  if (code != null) {
                    exchangeCodeForToken(code);
                    setState(() {
                      showWebView = false;
                    });
                  }
                }
                return NavigationDecision.navigate;
              },
            )
          : ElevatedButton(
              onPressed: initiateLogin,
              child: Text('Login with Google'),
            ),
    );
  }
}
```

## Environment Variables

The same environment variables are used for both web and mobile:

- `GOOGLE_CLIENT_ID`: Your Google OAuth client ID
- `GOOGLE_CLIENT_SECRET`: Your Google OAuth client secret
- `GOOGLE_REDIRECT_URI`: The redirect URI (should point to your callback endpoint)

## Google Cloud Console Configuration

For mobile apps, you need to:

1. **Add authorized redirect URIs**:
   - `https://your-api.com/api/auth/google/callback` (for web)
   - `https://your-api.com/api/auth/google/mobile/callback` (for mobile)

2. **Configure OAuth consent screen**:
   - Add your mobile app's bundle ID/package name
   - Configure scopes: `openid`, `email`, `profile`

3. **Create OAuth 2.0 credentials**:
   - Application type: Web application
   - Authorized redirect URIs: Include both web and mobile callback URLs

## Security Considerations

1. **HTTPS Required**: All OAuth endpoints must use HTTPS in production
2. **State Parameter**: Consider adding state parameter validation for additional security
3. **PKCE Flow**: For enhanced security, implement PKCE (Proof Key for Code Exchange)
4. **Token Storage**: Store JWT tokens securely in mobile app (use secure storage)
5. **Token Refresh**: Implement token refresh mechanism for long-lived sessions

## Testing

### Test the Mobile Endpoints

1. **Test `/mobile/login`**:
   ```bash
   curl -X GET "https://your-api.com/api/auth/google/mobile/login"
   ```

2. **Test `/mobile/token`**:
   ```bash
   curl -X POST "https://your-api.com/api/auth/google/mobile/token" \
        -H "Content-Type: application/x-www-form-urlencoded" \
        -d "code=your_authorization_code"
   ```

3. **Test `/debug`**:
   ```bash
   curl -X GET "https://your-api.com/api/auth/google/debug"
   ```

## Troubleshooting

### Common Issues

1. **"Invalid redirect_uri"**: Ensure the redirect URI in Google Console matches exactly
2. **"Authorization code expired"**: Authorization codes expire quickly, handle them promptly
3. **"Missing environment variables"**: Check all required environment variables are set
4. **CORS issues**: Ensure your API allows requests from your mobile app's domain

### Debug Endpoint

Use the `/debug` endpoint to check your OAuth configuration:

```bash
curl -X GET "https://your-api.com/api/auth/google/debug"
```

This will return the status of your environment variables and OAuth configuration.

## Migration from Web to Mobile

If you're migrating from web to mobile:

1. **Keep existing web endpoints** for backward compatibility
2. **Add mobile endpoints** alongside existing ones
3. **Update mobile app** to use new endpoints
4. **Test thoroughly** with both web and mobile flows
5. **Monitor logs** for any issues during transition

The mobile implementation maintains the same user authentication logic while providing mobile-friendly JSON responses instead of redirects. 