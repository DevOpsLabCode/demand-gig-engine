/**
 * Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
 * Purpose: Bootstraps React and loads base functionality followed by the final Build 13 visual system.
 */

import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./styles.css";
import "./auth.css";
import "./ui-refresh.css";
import "./owner-edit.css";
import "./auth-card-fit.css";
import "./phase2-discovery.css";
import "./lucky13.css";
import "./build13.css";
import "./professional-system.css";
import "./build13-acceptance.css";
import "./build13-art-direction.css";
import "./build13-email-status.css";
import "./build13-atlas-v2.css";
import "./build13-atlas-v3.css";
import "./build13-atlas-v4.css";
import "./build13-atlas-v6.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
