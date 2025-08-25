// js/config.js - Environment Configuration

// It checks if you are on your local machine or a live website.
const isLocal = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';

// replace this placeholder when you deploy your service.
const LIVE_API_URL = 'https://your-future-live-url.run.app';
const LIVE_WS_URL = 'wss://your-future-live-url.run.app';

const LOCAL_API_URL = 'http://localhost:8000';
const LOCAL_WS_URL = 'ws://localhost:8000';

const API_BASE_URL = isLocal ? LOCAL_API_URL : LIVE_API_URL;
const WS_BASE_URL = isLocal ? LOCAL_WS_URL : LIVE_WS_URL;

console.log(`Environment: ${isLocal ? 'Local' : 'Production'}`);
console.log(`API URL: ${API_BASE_URL}`);