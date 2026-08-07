/**
 * Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
 * Purpose: Bootstraps React and loads base, authentication, owner-edit, discovery, stabilization, Build 13, professional, acceptance, and Build 13.3 art-direction visual layers.
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

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
