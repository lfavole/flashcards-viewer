/**
 * Patch a `func` with a promise that:
 * * loads the script at the given `url`
 * * returns the actual result
 * This function is optimized for code golfing and takes less than 400 bytes when it is minified.
 */
function loadScript(url, func) {
    var parts = func.split(".");
    var partsLength = parts.length;
    // Returns a function in the global scope
    // e.g. getFunc(["Sentry", "init"]) == Sentry.init
    // (this creates Sentry = {init: ...})
    var getFunc = parts => parts.reduce((obj, prop) => {
        // If the property exists, return it, otherwise create it
        return obj[prop] ||= {};
    }, window);
    // Get the parent object and add the needed key to it
    return getFunc(parts.slice(0, partsLength - 1))[parts[partsLength - 1]] = function(...args) {
        // Load the script asynchronously (only when the function is called)
        return new Promise((resolve, reject) => {
            // Load the script...
            var script = document.createElement("script");
            script.src = `static/ext/${url}.js`;
            script.addEventListener("load", async function() {
                // ...and recall the function
                try {
                    resolve(await getFunc(parts)(...args));
                } catch(err) {
                    reject(err);
                }
            });
            script.addEventListener("error", reject);
            document.head.appendChild(script);
        });
    };
}

loadScript("jszip.min", "JSZip.loadAsync");
loadScript("sql-wasm", "initSqlJs");
loadScript("tablesort.min", "Tablesort");

// Settings come from https://github.com/ankitects/anki/blob/5f80ddf/ts/mathjax/index.ts#L26
// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

window.MathJax = {
    tex: {
        displayMath: [["\\[", "\\]"]],
        processEscapes: false,
        processEnvironments: false,
        processRefs: false,
        packages: {
            "[+]": ["noerrors", "mathtools", "mhchem"],
            "[-]": ["textmacros"],
        },
    },
    loader: {
        load: ["[tex]/noerrors", "[tex]/mathtools", "[tex]/mhchem"],
    },
    startup: {
        typeset: false,
    },
};
loadScript("mathjax/tex-chtml-full", "MathJax.typesetPromise");

// If there is no Sentry DSN: this will be removed
// If there is no Sentry DSN: the function expression will be simplified and the DSN will appear only once
(function() {
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
})();
