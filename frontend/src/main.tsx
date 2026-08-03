/**
 * Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
 * Purpose: Bootstraps React, attaches the application to the HTML root element, and enables development diagnostics.
 * Reading guide: JSDoc comments describe each exported contract and executable block.
 */

import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./styles.css";
import "./auth.css";

// Attach exactly one React root to the server-delivered HTML shell; StrictMode highlights unsafe development behavior.
ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
