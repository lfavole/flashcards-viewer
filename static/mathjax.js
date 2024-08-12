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
    typesetPromise: function(...args) {
        // Load MathJax asynchronously (only when the function is called)
        for(var element of args) {
            if(element.textContent.match(/\\\[.*\\\]/s)) {
                // If any of the elements contains math, load the script and recall the function
                return new Promise((resolve, reject) => {
                    var script = document.createElement("script");
                    script.src = "static/ext/mathjax.min.js";
                    script.addEventListener("load", function() {
                        MathJax.typesetPromise(...args).then(resolve());
                    });
                    script.addEventListener("error", reject);
                    document.head.appendChild(script);
                });
            }
        }
        // Otherwise return a promise that resolves immediatly
        return new Promise((resolve, reject) => resolve());
    },
};
