declare global {
  interface Window {
    SMARTDESK_CONFIG: {
      apiBase: string;
      oidcAuthority: string;
      oidcClientId: string;
      oidcScope: string;
    };
  }
}
export const config = window.SMARTDESK_CONFIG;
export const base = config.apiBase + "/api/v1";
