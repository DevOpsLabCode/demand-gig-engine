declare global {
  interface Window {
    fbq?: (...args: unknown[]) => void;
    _fbq?: unknown;
  }
}

let initializedPixel = "";

export function initMetaPixel(pixelId: string): void {
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

export function trackMetaEvent(
  name: string,
  parameters: Record<string, unknown> = {},
  eventId?: string,
): void {
  if (!window.fbq) return;
  if (eventId) window.fbq("track", name, parameters, { eventID: eventId });
  else window.fbq("track", name, parameters);
}
