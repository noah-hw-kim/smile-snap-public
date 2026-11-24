// js/config.js - Environment Configuration

// It checks if you are on your local machine or a live website.
const isLocal =
  window.location.hostname === "localhost" ||
  window.location.hostname === "127.0.0.1";

// replace this placeholder when you deploy your service.
const LIVE_API_URL =
  "https://vs6e4hx5jikv2gkngc6gvltr7a0rnbkv.lambda-url.us-east-1.on.aws";

const LOCAL_API_URL = "http://localhost:8000";

const API_BASE_URL = isLocal ? LOCAL_API_URL : LIVE_API_URL;

console.log(`Environment: ${isLocal ? "Local" : "Production"}`);
console.log(`API URL: ${API_BASE_URL}`);
