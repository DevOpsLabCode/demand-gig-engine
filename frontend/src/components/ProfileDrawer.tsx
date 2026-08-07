/**
 * Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
 * Purpose: Gives every member and professional role a complete profile with identity, location, social links, photos, uploaded videos, external media, and visible verification-email delivery status.
 */

import { ChangeEvent, FormEvent, useEffect, useMemo, useState } from "react";
import {
  BadgeCheck,
  Camera,
  CheckCircle2,
  ExternalLink,
  Film,
  Globe2,
  ImagePlus,
  Link2,
  LoaderCircle,
  MailCheck,
  MapPin,
  Music2,
  Plus,
  Save,
  Trash2,
  UserRound,
  X,
} from "lucide-react";
import { api } from "../api";
import type { AuthUser, ProfileMedia, ProfileMediaType, SocialLinkKey, SocialLinks } from "../types";
import { RoleManager } from "./RoleManager";

const API_BASE = import.meta.env.VITE_API_BASE ?? "/api";

interface Props {
  user: AuthUser;
  open: boolean;
  onClose: () => void;
  onUserChange: (user: AuthUser) => void;
}

interface EmailDeliveryStatus {
  ready: boolean;
  provider: string;
  sending_enabled: boolean;
  production_access: boolean;
  sender_verified: boolean;
  detail: string;
}

const SOCIAL_FIELDS: Array<{ key: SocialLinkKey; label: string; placeholder: string }> = [
  { key: "website", label: "Website", placeholder: "https://your-site.com" },
  { key: "youtube", label: "YouTube", placeholder: "https://youtube.com/@..." },
  { key: "instagram", label: "Instagram", placeholder: "https://instagram.com/..." },
  { key: "facebook", label: "Facebook", placeholder: "https://facebook.com/..." },
  { key: "tiktok", label: "TikTok", placeholder: "https://tiktok.com/@..." },
  { key: "spotify", label: "Spotify", placeholder: "https://open.spotify.com/artist/..." },
  { key: "soundcloud", label: "SoundCloud", placeholder: "https://soundcloud.com/..." },
  { key: "bandcamp", label: "Bandcamp", placeholder: "https://artist.bandcamp.com" },
];

function profileLabel(user: AuthUser) {
  if (user.account_type === "band") return "Artist / band profile";
  if (user.account_type === "venue") return "Venue profile";
  if (user.account_type === "organizer") return "Organizer profile";
  if (user.account_type === "sponsor") return "Sponsor profile";
  if (user.account_type === "rental") return "Equipment / vendor profile";
  return "Community member profile";
}

async function fetchEmailDeliveryStatus(): Promise<EmailDeliveryStatus> {
  const response = await fetch(`${API_BASE}/auth/email/status/`, { credentials: "include" });
  const body = await response.json().catch(() => ({})) as Partial<EmailDeliveryStatus> & { detail?: string };
  if (!response.ok) {
    throw new Error(body.detail || `Email status request failed (${response.status}).`);
  }
  return {
    ready: Boolean(body.ready),
    provider: String(body.provider || "unknown"),
    sending_enabled: Boolean(body.sending_enabled),
    production_access: Boolean(body.production_access),
    sender_verified: Boolean(body.sender_verified),
    detail: String(body.detail || "Email delivery status is unavailable."),
  };
}

export function ProfileDrawer({ user, open, onClose, onUserChange }: Props) {
  const [displayName, setDisplayName] = useState(user.display_name);
  const [bio, setBio] = useState(user.bio);
  const [city, setCity] = useState(user.city);
  const [state, setState] = useState(user.state);
  const [country, setCountry] = useState(user.country || "United States");
  const [headline, setHeadline] = useState("");
  const [genres, setGenres] = useState("");
  const [socialLinks, setSocialLinks] = useState<SocialLinks>({});
  const [externalVideos, setExternalVideos] = useState<string[]>([]);
  const [newVideo, setNewVideo] = useState("");
  const [media, setMedia] = useState<ProfileMedia[]>([]);
  const [preferredCities, setPreferredCities] = useState<string[]>(user.preferred_cities ?? []);
  const [newCity, setNewCity] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [emailDelivery, setEmailDelivery] = useState<EmailDeliveryStatus | null>(null);
  const [emailStatusLoading, setEmailStatusLoading] = useState(false);

  useEffect(() => {
    setDisplayName(user.display_name);
    setBio(user.bio);
    setCity(user.city);
    setState(user.state);
    setCountry(user.country || "United States");
    setPreferredCities(user.preferred_cities ?? []);
  }, [user]);

  useEffect(() => {
    if (!open) return;
    setError("");
    void api.discoveryProfile()
      .then((profile) => {
        setState(profile.state || user.state);
        setPreferredCities(profile.preferred_cities ?? []);
        setHeadline(profile.headline ?? "");
        setGenres((profile.genres ?? []).join(", "));
        setSocialLinks(profile.social_links ?? {});
        setExternalVideos(profile.external_video_urls ?? []);
        setMedia(profile.media ?? []);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Profile could not be loaded."));
  }, [open, user.state]);

  useEffect(() => {
    if (!open || user.email_verified) {
      setEmailDelivery(null);
      setEmailStatusLoading(false);
      return;
    }

    setEmailStatusLoading(true);
    void fetchEmailDeliveryStatus()
      .then((status) => setEmailDelivery(status))
      .catch((err) => {
        setEmailDelivery({
          ready: false,
          provider: "unknown",
          sending_enabled: false,
          production_access: false,
          sender_verified: false,
          detail: err instanceof Error ? err.message : "Email delivery status could not be loaded.",
        });
      })
      .finally(() => setEmailStatusLoading(false));
  }, [open, user.email_verified]);

  const avatar = useMemo(
    () => media.find((item) => item.media_type === "avatar")?.url || user.avatar_url,
    [media, user.avatar_url],
  );
  const cover = useMemo(() => media.find((item) => item.media_type === "cover")?.url || "", [media]);

  async function saveProfile(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const genreValues = genres.split(",").map((value) => value.trim()).filter(Boolean);
      const [updated] = await Promise.all([
        api.updateAuthProfile({
          display_name: displayName,
          bio,
          city,
          state,
          country,
          preferred_cities: preferredCities,
        }),
        api.updateDiscoveryProfile({
          state,
          preferred_cities: preferredCities,
          headline,
          genres: genreValues,
          social_links: socialLinks,
          external_video_urls: externalVideos,
        }),
      ]);
      onUserChange(updated);
      setMessage("Profile saved.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Profile could not be saved.");
    } finally {
      setBusy(false);
    }
  }

  async function upload(event: ChangeEvent<HTMLInputElement>, mediaType: ProfileMediaType) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const uploaded = await api.uploadProfileMedia(file, mediaType);
      setMedia((current) => [
        uploaded,
        ...current.filter((item) =>
          mediaType === "avatar" || mediaType === "cover" ? item.media_type !== mediaType : true,
        ),
      ]);
      const config = await api.authConfig();
      if (config.user) onUserChange(config.user);
      setMessage(mediaType === "video" ? "Video uploaded." : "Image uploaded.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setBusy(false);
    }
  }

  async function removeMedia(item: ProfileMedia) {
    setBusy(true);
    setError("");
    try {
      await api.deleteProfileMedia(item.id);
      setMedia((current) => current.filter((value) => value.id !== item.id));
      setMessage("Media removed.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Media could not be removed.");
    } finally {
      setBusy(false);
    }
  }

  async function resendVerification() {
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const result = await api.resendEmailVerification();
      setMessage(result.detail);
      const status = await fetchEmailDeliveryStatus();
      setEmailDelivery(status);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Verification email could not be sent.");
      try {
        setEmailDelivery(await fetchEmailDeliveryStatus());
      } catch {
        // Keep the resend error as the primary user-facing diagnostic.
      }
    } finally {
      setBusy(false);
    }
  }

  function addPreferredCity() {
    const value = newCity.trim();
    if (!value || preferredCities.includes(value) || preferredCities.length >= 12) return;
    setPreferredCities((current) => [...current, value]);
    setNewCity("");
  }

  function addExternalVideo() {
    const value = newVideo.trim();
    if (!value || externalVideos.includes(value) || externalVideos.length >= 8) return;
    setExternalVideos((current) => [...current, value]);
    setNewVideo("");
  }

  function updateSocialLink(key: SocialLinkKey, value: string) {
    setSocialLinks((current) => ({ ...current, [key]: value }));
  }

  if (!open) return null;

  return (
    <div className="profile-drawer-layer" role="presentation" onMouseDown={onClose}>
      <aside className="profile-drawer rich-profile-drawer" aria-label="Member profile" onMouseDown={(event) => event.stopPropagation()}>
        <div className="profile-drawer-header">
          <div><span className="section-kicker">Your Open Concert identity</span><h2>{profileLabel(user)}</h2></div>
          <button className="icon-button" type="button" onClick={onClose} aria-label="Close profile"><X /></button>
        </div>

        <div className="profile-cover-card" style={cover ? { backgroundImage: `url(${cover})` } : undefined}>
          <label className="cover-upload-button">
            <ImagePlus size={16} /> <span>{cover ? "Change cover" : "Add cover"}</span>
            <input type="file" accept="image/jpeg,image/png,image/webp" onChange={(event) => void upload(event, "cover")} />
          </label>
        </div>

        <div className="profile-identity-card profile-identity-overlap">
          <div className="profile-avatar-large">
            {avatar ? <img src={avatar} alt="" /> : <UserRound aria-hidden="true" />}
            <label className="avatar-upload-button" title="Upload profile photo"><Camera size={16} /><input type="file" accept="image/jpeg,image/png,image/webp" onChange={(event) => void upload(event, "avatar")} /></label>
          </div>
          <div>
            <strong>{user.display_name}</strong>
            <span>{user.email}</span>
            <div className={`verification-pill ${user.email_verified ? "is-verified" : "needs-verification"}`}>
              {user.email_verified ? <CheckCircle2 size={14} /> : <MailCheck size={14} />}
              {user.email_verified ? "Email verified" : "Email verification required"}
            </div>
          </div>
        </div>

        {!user.email_verified && (
          <div className="verification-callout">
            <MailCheck aria-hidden="true" />
            <div>
              <strong>Verify before Stage 2 approval</strong>
              <p>Verification protects fans, artists, venues, and organizers from impersonation and fake campaigns.</p>
              <div
                className={`verification-delivery-status ${emailDelivery?.ready ? "is-ready" : "is-blocked"}`}
                role="status"
                aria-live="polite"
              >
                <span>{emailStatusLoading ? "Checking email delivery…" : emailDelivery?.ready ? "Email service ready" : "Email delivery blocked"}</span>
                {!emailStatusLoading && emailDelivery && <small>{emailDelivery.detail}</small>}
              </div>
            </div>
            <button className="button secondary compact" type="button" onClick={() => void resendVerification()} disabled={busy || emailStatusLoading}>{busy ? "Sending…" : "Resend email"}</button>
          </div>
        )}

        <form className="profile-form" onSubmit={(event) => void saveProfile(event)}>
          <label>Display name<input value={displayName} onChange={(event) => setDisplayName(event.target.value)} maxLength={160} /></label>
          <label>Headline<input value={headline} onChange={(event) => setHeadline(event.target.value)} maxLength={180} placeholder={user.account_type === "band" ? "Brooklyn punk band · available for Northeast dates" : "One line that tells the network who you are"} /></label>
          <label>Bio<textarea value={bio} onChange={(event) => setBio(event.target.value)} rows={4} placeholder="Tell fans, artists, venues, and organizers who you are." /></label>
          <label><Music2 size={14} /> Genres / interests<input value={genres} onChange={(event) => setGenres(event.target.value)} placeholder="Punk, indie, jazz, electronic" /></label>

          <div className="profile-location-grid">
            <label><MapPin size={14} /> City<input value={city} onChange={(event) => setCity(event.target.value)} placeholder="New York" /></label>
            <label>State<input value={state} onChange={(event) => setState(event.target.value.toUpperCase())} placeholder="NY" maxLength={80} /></label>
          </div>
          <label>Country<input value={country} onChange={(event) => setCountry(event.target.value)} placeholder="United States" /></label>

          <div className="preferred-city-editor">
            <span>Cities you follow / perform in</span>
            <div className="preferred-city-input"><input value={newCity} onChange={(event) => setNewCity(event.target.value)} placeholder="Boston, MA" /><button type="button" className="icon-button" onClick={addPreferredCity} aria-label="Add followed city"><Plus /></button></div>
            <div className="city-chip-row">{preferredCities.map((value) => <button key={value} type="button" className="city-chip" onClick={() => setPreferredCities((current) => current.filter((item) => item !== value))}>{value} <X size={12} /></button>)}</div>
          </div>

          <section className="profile-links-editor">
            <div className="profile-subheading compact"><div><span className="section-kicker">Links</span><h3>Website & social channels</h3></div><Globe2 /></div>
            <div className="social-link-grid">
              {SOCIAL_FIELDS.map((field) => (
                <label key={field.key}>{field.label}<span className="profile-url-input"><Link2 size={15} /><input type="url" value={socialLinks[field.key] ?? ""} onChange={(event) => updateSocialLink(field.key, event.target.value)} placeholder={field.placeholder} /></span></label>
              ))}
            </div>
          </section>

          <section className="external-video-editor">
            <div className="profile-subheading compact"><div><span className="section-kicker">External video</span><h3>YouTube & social video</h3></div><Film /></div>
            <p className="profile-helper">Add YouTube, Vimeo, Twitch, Instagram, TikTok, or Facebook video links. Uploaded videos remain available below.</p>
            <div className="preferred-city-input"><input type="url" value={newVideo} onChange={(event) => setNewVideo(event.target.value)} placeholder="https://youtube.com/watch?v=..." /><button type="button" className="icon-button" onClick={addExternalVideo} aria-label="Add video link"><Plus /></button></div>
            <div className="external-video-list">
              {externalVideos.map((url) => (
                <div className="external-video-row" key={url}><ExternalLink size={15} /><a href={url} target="_blank" rel="noreferrer">{url}</a><button type="button" className="icon-button tiny" onClick={() => setExternalVideos((current) => current.filter((item) => item !== url))} aria-label="Remove video link"><X size={14} /></button></div>
              ))}
            </div>
          </section>

          <button className="button primary profile-save-button" type="submit" disabled={busy}>{busy ? <LoaderCircle className="spin" size={17} /> : <Save size={17} />} Save complete profile</button>
        </form>

        <section className="profile-media-section">
          <div className="profile-subheading"><div><span className="section-kicker">Media</span><h3>Photos & uploaded video</h3></div><BadgeCheck aria-hidden="true" /></div>
          <div className="media-upload-grid">
            <label className="media-upload-card"><ImagePlus /><strong>Add image</strong><span>JPG, PNG or WebP · 10 MB</span><input type="file" accept="image/jpeg,image/png,image/webp" onChange={(event) => void upload(event, "image")} /></label>
            <label className="media-upload-card"><Film /><strong>Add video</strong><span>MP4, WebM or MOV · 200 MB</span><input type="file" accept="video/mp4,video/webm,video/quicktime" onChange={(event) => void upload(event, "video")} /></label>
          </div>
          <div className="profile-media-grid">
            {media.filter((item) => item.media_type === "image" || item.media_type === "video").map((item) => (
              <article className="profile-media-item" key={item.id}>
                {item.media_type === "video" ? <video src={item.url} controls preload="metadata" /> : <img src={item.url} alt={item.caption || "Profile gallery"} />}
                <button type="button" className="media-delete" onClick={() => void removeMedia(item)} aria-label="Delete media"><Trash2 size={15} /></button>
              </article>
            ))}
          </div>
        </section>

        <details className="profile-role-section"><summary>Professional roles and verification</summary><RoleManager /></details>
        {message && <p className="message" role="status">{message}</p>}
        {error && <p className="error" role="alert">{error}</p>}
      </aside>
    </div>
  );
}
