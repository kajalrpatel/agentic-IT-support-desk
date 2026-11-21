import { UserManager, WebStorageStateStore } from "oidc-client-ts";
import { api, setAccessToken } from "../../../api/client";
import { config, base } from "../../../config/runtime";
async function startSession(): Promise<string> {
  const response = await fetch(base + "/auth/config");
  if (!response.ok)
    throw new Error("Unable to connect to sign-in. Please try again.");
  const settings = await response.json();
  if (settings.mode === "demo") {
    const response = await fetch(base + "/auth/demo", { method: "POST" });
    if (!response.ok)
      throw new Error("Could not start the local demo session.");
    const data = await response.json();
    setAccessToken(data.token);
    return data.email;
  }
  if (!config.oidcAuthority || !config.oidcClientId)
    throw new Error(
      "Sign-in is not configured. Ask your administrator to configure the identity provider.",
    );
  const manager = new UserManager({
    authority: config.oidcAuthority,
    client_id: config.oidcClientId,
    redirect_uri: window.location.origin + "/auth/callback",
    response_type: "code",
    scope: config.oidcScope,
    userStore: new WebStorageStateStore({ store: window.sessionStorage }),
  });
  if (window.location.pathname === "/auth/callback") {
    await manager.signinRedirectCallback();
    window.history.replaceState({}, "", "/");
  }
  const user = await manager.getUser();
  if (!user || user.expired) {
    await manager.signinRedirect();
    throw new Error("Redirecting to sign in…");
  }
  setAccessToken(user.access_token);
  return (await api<{ email: string }>("/me")).email;
}

// React StrictMode may mount effects twice; a sign-in attempt must stay single-flight.
let session: Promise<string> | undefined;
export function authenticate(): Promise<string> {
  return (session ??= startSession().catch((error) => {
    session = undefined;
    throw error;
  }));
}
