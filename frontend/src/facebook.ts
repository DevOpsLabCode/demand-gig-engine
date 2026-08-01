/**
 * Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
 * Purpose: Loads the Meta JavaScript SDK and returns an organizer access token
 * after an explicit Facebook Login action.
 */

interface FacebookAuthResponse {
  accessToken: string;
  expiresIn: number;
  signedRequest: string;
  userID: string;
  data_access_expiration_time?: number;
  graphDomain?: string;
}

interface FacebookLoginResponse {
  authResponse?: FacebookAuthResponse | null;
  status?: "connected" | "not_authorized" | "unknown" | string;
}

interface FacebookLoginOptions {
  scope: string;
  return_scopes: boolean;
  auth_type?: string;
}

interface FacebookInitOptions {
  appId: string;
  cookie: boolean;
  xfbml: boolean;
  version: string;
  status: boolean;
}

interface FacebookSdk {
  init(options: FacebookInitOptions): void;

  login(
    callback: (response: FacebookLoginResponse) => void,
    options: FacebookLoginOptions,
  ): void;
}

declare global {
  interface Window {
    FB?: FacebookSdk;
    fbAsyncInit?: () => void;
  }
}

const FACEBOOK_SDK_ELEMENT_ID = "facebook-jssdk";

const FACEBOOK_SDK_SOURCE =
  "https://connect.facebook.net/en_US/sdk.js";

const FACEBOOK_SDK_TIMEOUT_MS = 15_000;

let facebookSdkPromise: Promise<FacebookSdk> | null = null;

/**
 * Validate and normalize the Graph API version supplied by the backend.
 */
function normalizeGraphApiVersion(version: string): string {
  const normalized = version.trim();

  if (!/^v\d+\.\d+$/.test(normalized)) {
    throw new Error(
      `Invalid Facebook Graph API version: ${version}`,
    );
  }

  return normalized;
}

/**
 * Resolve the loaded Facebook SDK, adding the SDK script only once.
 */
function loadFacebookSdk(): Promise<FacebookSdk> {
  if (window.FB) {
    return Promise.resolve(window.FB);
  }

  if (facebookSdkPromise) {
    return facebookSdkPromise;
  }

  facebookSdkPromise = new Promise<FacebookSdk>(
    (resolve, reject) => {
      let settled = false;

      const finish = (
        callback: () => void,
      ) => {
        if (settled) {
          return;
        }

        settled = true;
        window.clearTimeout(timeoutId);
        callback();
      };

      const previousAsyncInit =
        window.fbAsyncInit;

      window.fbAsyncInit = () => {
        previousAsyncInit?.();

        if (!window.FB) {
          finish(() => {
            reject(
              new Error(
                "Facebook SDK initialized without exposing window.FB.",
              ),
            );
          });

          return;
        }

        finish(() => {
          resolve(window.FB as FacebookSdk);
        });
      };

      const timeoutId = window.setTimeout(
        () => {
          finish(() => {
            facebookSdkPromise = null;

            reject(
              new Error(
                "Facebook SDK did not load within 15 seconds.",
              ),
            );
          });
        },
        FACEBOOK_SDK_TIMEOUT_MS,
      );

      const existingScript =
        document.getElementById(
          FACEBOOK_SDK_ELEMENT_ID,
        );

      if (existingScript) {
        return;
      }

      const script =
        document.createElement("script");

      script.id = FACEBOOK_SDK_ELEMENT_ID;
      script.src = FACEBOOK_SDK_SOURCE;
      script.async = true;
      script.defer = true;
      script.crossOrigin = "anonymous";

      script.onerror = () => {
        finish(() => {
          facebookSdkPromise = null;

          reject(
            new Error(
              "Unable to download the Facebook JavaScript SDK.",
            ),
          );
        });
      };

      document.head.appendChild(script);
    },
  );

  return facebookSdkPromise;
}

/**
 * Open Facebook Login and return the user access token required by the
 * backend identity-verification and managed-Page endpoints.
 */
export async function loginWithFacebook(
  appId: string,
  graphApiVersion: string,
): Promise<string> {
  const normalizedAppId = appId.trim();

  if (!normalizedAppId) {
    throw new Error(
      "Facebook Login is unavailable because the Meta app ID is missing.",
    );
  }

  const normalizedVersion =
    normalizeGraphApiVersion(
      graphApiVersion,
    );

  const facebook =
    await loadFacebookSdk();

  facebook.init({
    appId: normalizedAppId,
    cookie: true,
    xfbml: false,
    version: normalizedVersion,
    status: false,
  });

  return new Promise<string>(
    (resolve, reject) => {
      facebook.login(
        (response) => {
          const accessToken =
            response.authResponse
              ?.accessToken
              ?.trim();

          if (
            response.status === "connected" &&
            accessToken
          ) {
            resolve(accessToken);
            return;
          }

          if (
            response.status ===
            "not_authorized"
          ) {
            reject(
              new Error(
                "Facebook Login completed, but the app was not authorized.",
              ),
            );

            return;
          }

          reject(
            new Error(
              "Facebook Login was cancelled or did not return an access token.",
            ),
          );
        },
        {
          scope: [
            "public_profile",
            "email",
            "pages_show_list",
            "pages_read_engagement",
            "pages_manage_posts",
          ].join(","),
          return_scopes: true,
        },
      );
    },
  );
}
