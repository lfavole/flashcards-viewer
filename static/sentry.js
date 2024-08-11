document.addEventListener("DOMContentLoaded", function() {
    var SENTRY_DSN = "";
    if(!SENTRY_DSN) return;

    var script = document.createElement("script");
    script.src = "static/ext/bundle.tracing.replay.min.js";
    script.addEventListener("load", function() {
        Sentry.init({
            dsn: SENTRY_DSN,
            integrations: [
                Sentry.browserTracingIntegration(),
                Sentry.replayIntegration(),
            ],
            // Performance Monitoring
            tracesSampleRate: 1.0,
            // Session Replay
            replaysSessionSampleRate: 0.1,
            replaysOnErrorSampleRate: 1.0,
            profilesSampleRate: 1.0,
        });
    });
    document.head.appendChild(script);
});
