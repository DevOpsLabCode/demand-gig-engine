/**
 * Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
 * Purpose: Gives members a right-side profile workspace for identity, location, verification, roles, photos, and videos.
 */

import { ChangeEvent, FormEvent, useEffect, useMemo, useState } from "react";
import {
  BadgeCheck,
  Camera,
  CheckCircle2,
  Film,
  ImagePlus,
  LoaderCircle,
  MailCheck,
  MapPin,
  Plus,
  Save,
  Trash2,
  UserRound,
  X,
} from "lucide-react";
import { api } from "../api";
import type { AuthUser, ProfileMedia, ProfileMediaType } from "../types";
import { RoleManager } from "./RoleManager";

interface Props {
  user: AuthUser;
  open: boolean;
  onClose: () => void;
  onUserChange: (user: AuthUser) => void;
}

export function ProfileDrawer({ user, open, onClose, onUserChange }: Props) {
  const [displayName, setDisplayName] = useState(user.display_name);
  const [bio, setBio] = useState(user.bio);
  const [city, setCity] = useState(user.city);
  const [state, setState] = useState(user.state);
  const [country, setCountry] = useState(user.country || "United States");
  const [media, setMedia] = useState<ProfileMedia[]>([]);
  const [preferredCities, setPreferredCities] = useState<string[]>(user.preferred_cities ?? []);
  const [newCity, setNewCity] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

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
    void api.listProfileMedia().then(setMedia).catch(() => setMedia([]));
  }, [open]);

  const avatar = useMemo(
    () => media.find((item) => item.media_type === "avatar")?.url || user.avatar_url,
    [media, user.avatar_url],
  );

  async function saveProfile(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const updated = await api.updateAuthProfile({
        display_name: displayName,
        bio,
        city,
        state,
        country,
        preferred_cities: preferredCities,
      });
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
      setError(err instanceof Error ? err.message : "Upload failed.");
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
    } catch (err) {
      setError(err instanceof Error ? err.message : "Verification email could not be sent.");
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

  if (!open) return null;

  return (
    <div className="profile-drawer-layer" role="presentation" onMouseDown={onClose}>
      <aside
        className="profile-drawer"
        aria-label="Member profile"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <div className="profile-drawer-header">
          <div>
            <span className="section-kicker">Your Open Concert identity</span>
            <h2>Profile</h2>
          </div>
          <button className="icon-button" type="button" onClick={onClose} aria-label="Close profile">
            <X />
          </button>
        </div>

        <div className="profile-identity-card">
          <div className="profile-avatar-large">
            {avatar ? <img src={avatar} alt="" /> : <UserRound aria-hidden="true" />}
            <label className="avatar-upload-button" title="Upload profile photo">
              <Camera size={16} />
              <input type="file" accept="image/jpeg,image/png,image/webp" onChange={(event) => void upload(event, "avatar")} />
            </label>
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
              <p>You can explore and complete your profile now. A verified email is required before a campaign can be publicly approved.</p>
            </div>
            <button className="button secondary compact" type="button" onClick={() => void resendVerification()} disabled={busy}>
              Resend email
            </button>
          </div>
        )}

        <form className="profile-form" onSubmit={(event) => void saveProfile(event)}>
          <label>
            Display name
            <input value={displayName} onChange={(event) => setDisplayName(event.target.value)} maxLength={160} />
          </label>
          <label>
            Bio
            <textarea value={bio} onChange={(event) => setBio(event.target.value)} rows={4} placeholder="Tell artists, venues, and fans who you are." />
          </label>
          <div className="profile-location-grid">
            <label>
              <MapPin size={14} /> City
              <input value={city} onChange={(event) => setCity(event.target.value)} placeholder="New York" />
            </label>
            <label>
              State
              <input value={state} onChange={(event) => setState(event.target.value.toUpperCase())} placeholder="NY" maxLength={80} />
            </label>
          </div>
          <label>
            Country
            <input value={country} onChange={(event) => setCountry(event.target.value)} placeholder="United States" />
          </label>

          <div className="preferred-city-editor">
            <span>Cities you follow</span>
            <div className="preferred-city-input">
              <input value={newCity} onChange={(event) => setNewCity(event.target.value)} placeholder="Boston, MA" />
              <button type="button" className="icon-button" onClick={addPreferredCity} aria-label="Add followed city"><Plus /></button>
            </div>
            <div className="city-chip-row">
              {preferredCities.map((value) => (
                <button key={value} type="button" className="city-chip" onClick={() => setPreferredCities((current) => current.filter((item) => item !== value))}>
                  {value} <X size={12} />
                </button>
              ))}
            </div>
          </div>

          <button className="button primary" type="submit" disabled={busy}>
            {busy ? <LoaderCircle className="spin" size={17} /> : <Save size={17} />}
            Save profile
          </button>
        </form>

        <section className="profile-media-section">
          <div className="profile-subheading">
            <div>
              <span className="section-kicker">Media</span>
              <h3>Show who you are</h3>
            </div>
            <BadgeCheck aria-hidden="true" />
          </div>

          <div className="media-upload-grid">
            <label className="media-upload-card">
              <ImagePlus />
              <strong>Add image</strong>
              <span>JPG, PNG or WebP · 10 MB</span>
              <input type="file" accept="image/jpeg,image/png,image/webp" onChange={(event) => void upload(event, "image")} />
            </label>
            <label className="media-upload-card">
              <Film />
              <strong>Add video</strong>
              <span>MP4, WebM or MOV · 200 MB</span>
              <input type="file" accept="video/mp4,video/webm,video/quicktime" onChange={(event) => void upload(event, "video")} />
            </label>
          </div>

          <div className="profile-media-grid">
            {media.filter((item) => item.media_type === "image" || item.media_type === "video").map((item) => (
              <article className="profile-media-item" key={item.id}>
                {item.media_type === "video" ? (
                  <video src={item.url} controls preload="metadata" />
                ) : (
                  <img src={item.url} alt={item.caption || "Profile gallery"} />
                )}
                <button type="button" className="media-delete" onClick={() => void removeMedia(item)} aria-label="Delete media">
                  <Trash2 size={15} />
                </button>
              </article>
            ))}
          </div>
        </section>

        <details className="profile-role-section">
          <summary>Professional roles and verification</summary>
          <RoleManager />
        </details>

        {message && <p className="message" role="status">{message}</p>}
        {error && <p className="error" role="alert">{error}</p>}
      </aside>
    </div>
  );
}
