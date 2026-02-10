import { Auth0ProviderOptions } from '@auth0/auth0-spa-js';

export const authConfig: Auth0ProviderOptions = {
  domain: process.env.REACT_APP_AUTH_DOMAIN || 'localhost:8080',
  clientId: process.env.REACT_APP_CLIENT_ID || 'reports-frontend',
  authorizationParams: {
    redirect_uri: window.location.origin,
    audience: 'reports-api',
    scope: 'openid profile email roles read:reports write:reports'
  },
  useRefreshTokens: true,
  cacheLocation: 'localstorage'
};

export const oidcConfig = {
  authority: `http://${process.env.REACT_APP_AUTH_DOMAIN || 'localhost:8080'}/realms/reports-realm`,
  client_id: process.env.REACT_APP_CLIENT_ID || 'reports-frontend',
  redirect_uri: `${window.location.origin}/callback`,
  response_type: 'code',
  scope: 'openid profile email roles read:reports write:reports',
  post_logout_redirect_uri: window.location.origin,
  automaticSilentRenew: true,
  loadUserInfo: true,
  pkceMethod: 'S256'
};