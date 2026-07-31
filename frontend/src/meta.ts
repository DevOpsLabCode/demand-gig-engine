/**
 * Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
 * Purpose: Initializes Meta Pixel and emits browser conversion events with deduplication identifiers.
 * Reading guide: JSDoc comments describe each exported contract and executable block.
 */

declare global {
  /**
   * Extend Window with the Meta Pixel queue function installed by the external script.
   */
  interface Window {
    fbq?: (...args: unknown[]) => void;
    _fbq?: unknown;
  }
}

let initializedPixel = "";

/**
 * Initialize Meta Pixel exactly once per pixel ID, queue calls until the SDK loads, and record the initial PageView.
 */
export function initMetaPixel(pixelId: string): void {
  // Skip server-side rendering, missing configuration, and duplicate initialization for the same pixel.
  if (!pixelId || initializedPixel === pixelId || typeof document === "undefined") return;

  const fbq = function (...args: unknown[]) {
    const queueOwner = fbq as typeof fbq & { callMethod?: (...items: unknown[]) => void; queue?: unknown[] };
    if (queueOwner.callMethod) queueOwner.callMethod(...args);
    else (queueOwner.queue ??= []).push(args);
  };
  const stateful = fbq as typeof fbq & { loaded?: boolean; version?: string; queue?: unknown[] };
  stateful.loaded = true;
  stateful.version = "2.0";
  stateful.queue = [];
  window.fbq = window.fbq ?? fbq;
  window._fbq = window._fbq ?? window.fbq;

  if (!document.querySelector('script[data-vibesmeet-meta-pixel="true"]')) {
    const script = document.createElement("script");
    script.async = true;
    script.src = "https://connect.facebook.net/en_US/fbevents.js";
    script.dataset.vibesmeetMetaPixel = "true";
    document.head.appendChild(script);
  }

  window.fbq("init", pixelId);
  window.fbq("track", "PageView");
  initializedPixel = pixelId;
}

/**
 * Emit a browser conversion event and include eventID when server-side Conversions API deduplication is used.
 */
export function trackMetaEvent(
  name: string,
  parameters: Record<string, unknown> = {},
  eventId?: string,
): void {
  // Tracking is optional; application behavior must continue when Pixel is unavailable or blocked.
  if (!window.fbq) return;
  if (eventId) window.fbq("track", name, parameters, { eventID: eventId });
  else window.fbq("track", name, parameters);
}
