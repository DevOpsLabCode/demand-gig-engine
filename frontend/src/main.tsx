/**
 * Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
 * Purpose: Bootstraps React and loads the base, authentication, and Phase 2.5 UI design layers.
 */

import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./styles.css";
import "./auth.css";
import "./ui-refresh.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
