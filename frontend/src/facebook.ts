declare global {
  interface Window {
    FB?: {
      init(options: Record<string, unknown>): void;
      login(
        callback: (response: FacebookLoginResponse) => void,
        options: Record<string, unknown>,
      ): void;
    };
    fbAsyncInit?: () => void;
  }
}

interface FacebookLoginResponse {
  authResponse?: { accessToken: string };
  status?: string;
}

let loadedAppId = "";

export async function loadFacebookSdk(appId: string, version: string): Promise<void> {
  if (!appId) throw new Error("Facebook App ID is not configured.");
  if (window.FB && loadedAppId === appId) return;

  await new Promise<void>((resolve, reject) => {
    const existing = document.getElementById("facebook-jssdk") as HTMLScriptElement | null;
    window.fbAsyncInit = () => {
      window.FB?.init({ appId, cookie: true, xfbml: false, version });
      loadedAppId = appId;
      resolve();
    };
    if (existing) {
      if (window.FB) window.fbAsyncInit();
      else existing.addEventListener("load", () => window.fbAsyncInit?.(), { once: true });
      return;
    }
    const script = document.createElement("script");
    script.id = "facebook-jssdk";
    script.async = true;
    script.defer = true;
    script.crossOrigin = "anonymous";
    script.src = "https://connect.facebook.net/en_US/sdk.js";
    script.onerror = () => reject(new Error("Could not load the Facebook SDK."));
    document.body.appendChild(script);
  });
}

export async function loginWithFacebook(appId: string, version: string): Promise<string> {
  await loadFacebookSdk(appId, version);
  return new Promise<string>((resolve, reject) => {
    window.FB?.login(
      (response) => {
        const token = response.authResponse?.accessToken;
        if (token) resolve(token);
        else reject(new Error("Facebook connection was canceled or not authorized."));
      },
      {
        scope: "public_profile,email,pages_show_list,pages_read_engagement,pages_manage_posts",
        return_scopes: true,
        auth_type: "rerequest",
      },
    );
  });
}
