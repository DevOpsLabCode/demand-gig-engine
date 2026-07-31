/**
 * Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
 * Purpose: Creates tracked Facebook links, connects an organizer account, lists managed Pages, and publishes campaign messages.
 * Reading guide: JSDoc comments describe each exported contract and executable block.
 */

import { useEffect, useMemo, useState } from "react";
import { Copy, Facebook, Send, Users } from "lucide-react";
import { api } from "../api";
import { loginWithFacebook } from "../facebook";
import type { Campaign, FacebookConfig, FacebookPage, FacebookProfile, FacebookShareLink } from "../types";

/**
 * Receive the active campaign and a callback for presenting integration status to the surrounding card.
 */
interface Props {
  campaign: Campaign;
  onMessage: (message: string) => void;
}

/**
 * Coordinate manual Group sharing, tracked-link copying, Facebook Login, managed-Page discovery, and Page publication.
 */
export function FacebookIntegration({ campaign, onMessage }: Props) {
  const query = useMemo(() => new URLSearchParams(window.location.search), []);
  const [config, setConfig] = useState<FacebookConfig | null>(null);
  const [groupName, setGroupName] = useState(query.get("group") ?? "");
  const [referralCode, setReferralCode] = useState(query.get("ref") ?? "");
  const [shareLink, setShareLink] = useState<FacebookShareLink | null>(null);
  const [profile, setProfile] = useState<FacebookProfile | null>(null);
  const [pages, setPages] = useState<FacebookPage[]>([]);
  const [selectedPageId, setSelectedPageId] = useState("");
  const [accessToken, setAccessToken] = useState("");
  const [busy, setBusy] = useState(false);

  // Load only public capability/configuration data; Meta secrets stay on the Django server.
  useEffect(() => {
    api.facebookConfig().then(setConfig).catch(() => setConfig(null));
  }, []);

  /** Ask the backend to sign a tracked URL carrying community and referral attribution. */
  async function generateLink(): Promise<FacebookShareLink> {
    const link = await api.facebookShareLink(campaign.slug, {
      source: "facebook_group",
      group_name: groupName,
      referral_code: referralCode,
    });
    setShareLink(link);
    return link;
  }

  /** Open Facebook Share in a popup using the tracked URL; Group selection remains a user-controlled Meta action. */
  async function shareToFacebook() {
    setBusy(true);
    try {
      const link = shareLink ?? await generateLink();
      window.open(link.share_dialog_url, "facebook-share", "width=720,height=640");
      onMessage("Facebook Share opened with a tracked campaign link.");
    } catch (error) {
      onMessage(error instanceof Error ? error.message : "Could not create Facebook share link.");
    } finally {
      setBusy(false);
    }
  }

  /** Copy the same attributed campaign URL for Facebook Events, Groups, Messenger, WhatsApp, or other communities. */
  async function copyTrackedLink() {
    setBusy(true);
    try {
      const link = shareLink ?? await generateLink();
      await navigator.clipboard.writeText(link.campaign_url);
      onMessage("Tracked link copied. Paste it into the Facebook Event, Group, Page, Messenger, or WhatsApp chat.");
    } catch (error) {
      onMessage(error instanceof Error ? error.message : "Could not copy the link.");
    } finally {
      setBusy(false);
    }
  }

  /** Obtain a user token in the browser, verify it on the backend, and load Pages the organizer may manage. */
  async function connectFacebook() {
    if (!config?.enabled) {
      onMessage("Configure META_APP_ID and META_APP_SECRET to connect Facebook Pages.");
      return;
    }
    setBusy(true);
    try {
      const token = await loginWithFacebook(config.app_id, config.graph_api_version);
      const [connectedProfile, managedPages] = await Promise.all([
        api.facebookLogin(token),
        api.facebookPages(token),
      ]);
      setAccessToken(token);
      setProfile(connectedProfile);
      setPages(managedPages);
      setSelectedPageId(managedPages[0]?.id ?? "");
      onMessage(`Connected as ${connectedProfile.name}. ${managedPages.length} managed Page(s) available.`);
    } catch (error) {
      onMessage(error instanceof Error ? error.message : "Facebook connection failed.");
    } finally {
      setBusy(false);
    }
  }

  /** Publish a tracked campaign message to the selected managed Page through the backend Graph API adapter. */
  async function publishToPage() {
    const page = pages.find((item) => item.id === selectedPageId);
    if (!page) {
      onMessage("Choose a Facebook Page first.");
      return;
    }
    setBusy(true);
    try {
      const result = await api.publishFacebookPage(campaign.slug, {
        page_id: page.id,
        page_access_token: page.page_access_token,
        source: "facebook_page",
        referral_code: referralCode || `page-${page.id}`,
        message: `${campaign.title}\n\n${campaign.pitch}\n\nSupport the seed. The artist and venue are confirmed only after enough fans commit.`,
      });
      onMessage(`Published to ${page.name}. Facebook post ID: ${result.post_id}`);
    } catch (error) {
      onMessage(error instanceof Error ? error.message : "Could not publish to the Facebook Page.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="facebook-integration">
      <div className="facebook-title"><Facebook size={19} /> Facebook organizer integration</div>
      <p className="facebook-note">
        Use Facebook Events and Groups for discovery, then route supporters to a tracked gig seed where demand, deposits, sponsors, and conversion are verified.
      </p>
      <div className="facebook-grid">
        <label>Facebook Group or community name
          <input value={groupName} onChange={(event) => { setGroupName(event.target.value); setShareLink(null); }} placeholder="Band X NYC Fans" />
        </label>
        <label>Organizer/referral code
          <input value={referralCode} onChange={(event) => { setReferralCode(event.target.value); setShareLink(null); }} placeholder="admin-jane" />
        </label>
      </div>
      <div className="facebook-actions">
        <button type="button" className="facebook-button" disabled={busy} onClick={shareToFacebook}><Facebook size={17} /> Share on Facebook</button>
        <button type="button" className="secondary" disabled={busy} onClick={copyTrackedLink}><Copy size={17} /> Copy tracked link</button>
        <button type="button" className="secondary" disabled={busy} onClick={connectFacebook}><Users size={17} /> {profile ? `Connected: ${profile.name}` : "Connect Facebook Pages"}</button>
      </div>
      {shareLink && <input className="share-url" value={shareLink.campaign_url} readOnly aria-label="Tracked Facebook campaign URL" />}
      {pages.length > 0 && (
        <div className="page-publisher">
          <select value={selectedPageId} onChange={(event) => setSelectedPageId(event.target.value)}>
            {pages.map((page) => <option key={page.id} value={page.id}>{page.name}{page.category ? ` — ${page.category}` : ""}</option>)}
          </select>
          <button type="button" className="facebook-button" disabled={busy || !accessToken} onClick={publishToPage}><Send size={17} /> Publish campaign to Page</button>
        </div>
      )}
      <small>
        Facebook Group member import and automatic Group posting are intentionally unavailable because Meta retired the Groups API. Group administrators share the tracked link manually; VibesMeet measures every resulting supporter and commitment.
      </small>
    </section>
  );
}
