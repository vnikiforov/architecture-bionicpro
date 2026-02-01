import { Auth0ProviderOptions } from '@auth0/auth0-spa-js';

export const authConfig: Auth0ProviderOptions = {
  domain: 'localhost:8080', // Или ваш Keycloak domain
  clientId: 'reports-frontend',
  authorizationParams: {
    redirect_uri: window.location.origin,
    audience: 'reports-api',
    scope: 'openid profile email roles'
  },
  useRefreshTokens: true,
  cacheLocation: 'localstorage' 
  // PKCE включен по умолчанию в @auth0/auth0-spa-js
};

// Альтернативно, с использованием oidc-client-ts:
export const oidcConfig = {
  authority: 'http://localhost:8080/realms/reports-realm',
  client_id: 'reports-frontend',
  redirect_uri: 'http://localhost:3000/callback',
  response_type: 'code',               // Authorization Code Flow
  scope: 'openid profile email roles',
  post_logout_redirect_uri: 'http://localhost:3000/',
  automaticSilentRenew: true,
  loadUserInfo: true,
  pkceMethod: 'S256'                   // Включение PKCE
};