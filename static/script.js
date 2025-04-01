var translations = {en: {}};
var config = {language: "en"};
var languages = {"fr": "static/fr.js"};
var sqlSource = "static/ext/sql-wasm.wasm";

function loadLanguage(lang) {
    lang = lang.split("-")[0];
    if(!(lang in languages)) return;

    var script = document.createElement("script");
    script.src = "static/" + lang + ".js";
    script.addEventListener("load", function() {
        AlpineI18n.locale = lang;
    });
    document.head.appendChild(script);
    return true;
}

function setupTranslations() {
    for(var lang of navigator.languages) {
        if(loadLanguage(lang)) return;
    }
}

window.addEventListener("DOMContentLoaded", function() {
    // Setup Tablesort on all the existing tables...
    var tables = document.querySelectorAll("table");
    for(var table of tables) {
        new Tablesort(table);
    }
    // ...and on all newly created tables
    var observer = new MutationObserver(function(mutations) {
        for(var mutation of mutations) {
            for(var node of mutation.addedNodes) {
                if(node.tagName == "TABLE" && node.classList.contains("sort"))
                    new Tablesort(node);
            }
        }
    });
    observer.observe(document.body, {childList: true, subtree: true});

    // Setup the service worker
    if("serviceWorker" in navigator) {
        navigator.serviceWorker.register("sw.js")
        .then(function(reg) {
            console.log(`Service worker registration succeeded. Scope is ${reg.scope}`);
        })
        .catch(function(error) {
            console.error("Service worker registration failed:", error);
        });
    }

    // Setup Eruda if needed
    if(new URLSearchParams(location.search).get("eruda")) {
        var script = document.createElement("script");
        script.src = "static/eruda.min.js";
        script.addEventListener("load", function() {
            eruda.init();
        });
        document.head.appendChild(script);
    }
});

function sqlToDict(sql) {
    var ret = [];
    var dict, i, l;
    for(var row of sql[0].values) {
        dict = {};
        for(i = 0, l = row.length; i < l; i++) {
            dict[sql[0].columns[i]] = row[i];
        }
        ret.push(dict);
    }
    return ret;
}

function _recursiveOpenEntry(item, openFunc) {
    if(item.isFile)
        item.file(openFunc);

    if (item.isDirectory) {
        var directoryReader = item.createReader();
        directoryReader.readEntries((entries) => {
            entries.forEach(entry => _recursiveOpenEntry(entry, openFunc));
        });
    }
}

async function _recursiveOpenHandle(item, openFunc) {
    for await (file of item.values()) {
        if(file instanceof FileSystemDirectoryHandle)
            _recursiveOpenHandle(file, openFunc);
        else
            openFunc(file);
    }
}

async function recursiveOpen(dataTransfer, openFunc, test = false) {
    // Array of files or URLs
    if(dataTransfer.length !== undefined) {
        [...dataTransfer].forEach(openFunc);
        return;
    }

    // Old DataTransfer or file input
    if(!("items" in dataTransfer)) {
        [...dataTransfer.files].forEach(openFunc);
        return;
    }

    for(var item of dataTransfer.items) {
        if(item.kind == "file") {
            if(test) {
                openFunc();
                continue;
            }
            var entry = item.getAsFileSystemHandle?.();
            if(entry) {
                await _recursiveOpenHandle(entry, openFunc);
            } else {
                entry = item.getAsEntry?.() || item.webkitGetAsEntry?.();
                if(entry) {
                    _recursiveOpenEntry(entry, openFunc);
                } else {
                    throw new Error("Could not open files, APIs are not available");
                }
            }
        } else if(item.type == "text/plain" || item.type == "text/uri-list") {
            item.getAsString(openFunc);
        }
    }
}

async function getCount(dataTransferOrInput) {
    var count = 0;
    var open = () => count++;
    await recursiveOpen(dataTransferOrInput, open, true);
    return count;
}

async function addFilesTo(dataTransferOrInput, files) {
    await recursiveOpen(dataTransferOrInput, async file => {
        if(!file) return;
        files[file?.name || decodeURIComponent(file.replace(/^.*[/\\]/, ""))] = await openAndParseFile(file);
    });
}

async function openAndParseFile(file) {
    if(!file) return;

    if(typeof file == "string") {
        // Fetch the file
        var resp = await fetch(file);
        if(resp.status != 200 && resp.status != 0)
            throw new Error(resp.statusText);
        var file = resp.blob();
    }
    var zip = await JSZip.loadAsync(file);
    var buf = await zip.file("collection.anki21").async("uint8array");

    var media = await zip.file("media").async("text");

    var SQL = await initSqlJs({locateFile: f => f == "sql-wasm.wasm" ? sqlSource : "static/ext/" + f});
    var db = new SQL.Database(buf);

    var col_info = sqlToDict(db.exec("SELECT models, decks FROM col"))[0];
    // https://stackoverflow.com/a/8161801
    // https://dba.stackexchange.com/a/315294
    var notes = sqlToDict(db.exec("SELECT notes.mid, notes.mod, notes.tags, notes.flds, notes.sfld, cards.did FROM notes LEFT JOIN cards ON notes.id = cards.nid AND cards.id = (SELECT id FROM cards WHERE notes.id = cards.nid LIMIT 1)"));
    return {
        models: cleanupModels(JSON.parse(col_info.models)),
        decks: cleanupDecks(JSON.parse(col_info.decks), notes),
        notes: notes,
        media: JSON.parse(media),
        zip: zip,
    };
}

/**
 * Sort an object by its keys or with the specified function.
 */
function sortObject(obj, fn) {
    var ret = {};
    var fn = fn || (e => e[0]);
    Object.entries(obj).sort((a, b) => fn(a[0], a[1]).localeCompare(fn(b[0], b[1])))
    .forEach(item => ret[item[0]] = obj[item[0]]);
    return ret;
}

/**
 * Given a deck name, return all the names of its parent decks.
 */
function getParentDecks(deckName) {
    var candidate = deckName;
    var ret = [];
    while(candidate.includes("::")) {
        candidate = candidate.replace(/^(.*)::.*?$/, "$1");
        ret.push(candidate);
    }
    return ret;
}

/**
 * Return an object that maps a deck ID to a deck name.
 */
function getDeckNameIds(decks) {
    var ret = {};
    for(var deckId in decks)
        ret[decks[deckId].name] = +deckId;
    return ret;
}

/**
 * Cleanup a models object: add an ID to the templates.
 */
function cleanupModels(models) {
    for(var model of Object.values(models)) {
        for(var [id, template] of Object.entries(model.tmpls)) {
            template.id = id;
        }
    }
    return models;
}

/**
 * Cleanup a decks list:
 * * Remove the "Default" deck if it is empty
 * * Add non-existent parent decks
 * * Add parent deck IDs
 * * Sort the list
 * * Make the list reactive
 */
function cleanupDecks(decks, notes) {
    // Remove the "Default" deck
    if(decks[1] && decks[1].name == "Default" && !getNotes({notes: notes}, {id: 1}).length)
        delete decks[1];

    // Build a list of deck names
    var deckNames = [];
    for(var deckId in decks) {
        deckNames.push(decks[deckId].name);
    }
    // Add non-existent parent decks
    // If A::B::C exists, A::B has to exist,
    // otherwise A::B::C will be unaccessible from the interface.
    for(var deckName of deckNames) {
        // Loop over all parent decks...
        for(var deckNameToTry of getParentDecks(deckName)) {
            // ...and check if they exist
            if(!deckNames.includes(deckNameToTry)) {
                // If a parent deck doesn't exist, add it
                id = +(Math.random() + "").substring(2);
                decks[id] = {name: deckNameToTry, id: id, collapsed: true};
            }
        }
    }

    // Build a list to get the ID of a deck with its name
    var deckNameIds = {};
    for(var deckId in decks) {
        deckNameIds[decks[deckId].name] = +deckId;
    }
    // Add deck IDs and parent deck IDs
    for(var deckId in decks) {
        var deckName = decks[deckId].name
        decks[deckId].id = deckId;
        decks[deckId].hasChildren = !!deckNames.filter(name => name.startsWith(deckName + "::")).length;
        decks[deckId].parentId = deckName.includes("::") ? deckNameIds[deckNameToTry.replace(/::.*?$/, "")] : 0;
    }

    // Sort the decks list...
    decks = sortObject(decks, (deckId, deck) => deck.name);
    // and make it reactive
    for(var deckId in decks) {
        decks[deckId] = Alpine.reactive(decks[deckId]);
    }

    return decks;
}

function isHidden(deck, decks) {
    var deckNameIds = getDeckNameIds(decks);

    for(var parentDeckName of getParentDecks(decks[deck.id].name)) {
        // if a parent deck is collapsed, the deck is hidden
        if(decks[deckNameIds[parentDeckName]].collapsed)
            return true;
    }
    return false;
}

/** Get the templates of a model.
 * @param {Object} file - The file object
 * @param {Object} note - The note object
 */
function getTemplates(file, note) {
    var model = file.models[note.mid];
    if (model.type == 1) {
        return getClozesNumbers(model, note).map(n => {
            var tmpl = JSON.parse(JSON.stringify(model.tmpls[0]));
            tmpl.ord = n;
            tmpl.name = "Carte " + n;
            return tmpl;
        });
    }
    return model.tmpls;
}

function getNotes(file, deck) {
    return file.notes.filter(e => e.did == +deck.id);
}

function stripHTML(html) {
    return html
    .replace(/<img[^>]+alt="([^"]+)"[^>]*>/g, "$1 ")
    .replace(/<img[^>]+src="([^"]+)"[^>]*>/g, "$1 ")
    .replace(/<(style|script)[^>]*>[^]*?<\/\1>/gm, "")
    .replace(/<\/(div|li|ul|p)>|<br>/g, "\n")
    .replace(/<[^>]+>/g, "")
    .replace(/ {2,}/g, " ")
    .replace(/\n{2,}/g, "\n")
    .trim();
}

var FIELDS = {
    sfld: "Sort field",
    question: "Question",
    answer: "Answer",
};

function getField(note, field, file) {
    if(field == "question")
        return stripHTML(render(file.models[note.mid], file.models[note.mid].tmpls[0], note, false, true));
    if(field == "answer")
        return stripHTML(render(file.models[note.mid], file.models[note.mid].tmpls[0], note, true, true));
    return note[field];
}

async function getMediaURL(path, file) {
    var item;
    for(var itemToTry in file.media) {
        if(file.media[itemToTry] == path) {
            item = itemToTry;
            break;
        }
    }
    if(!item) return;
    var blob = await file.zip.files[item].async("blob");
    return URL.createObjectURL(blob);
}

async function patchMediaURLs(html, file) {
    var parts = html.split(/(<img[^>]+src="|<link[^>]+href="|<script[^>]+src=")([^"]+)("[^>]*>)/g);
    // [before_tag, before, url, after, ...]
    var ret = "";
    for(var i = 0, l = parts.length; i < l; i++) {
        if(i % 4 == 2)  // URL
            ret += await getMediaURL(parts[i], file);
        else  // normal text
            ret += parts[i];
    }
    var cssImports = [];
    // import and import url
    ret = ret.replace(/@import\s+(?:url\(["']?([^"'\)]+)["']?\)(?:\s+[^;]+)?|["']([^"']+)["'](?:\s+[^;]+)?)\s*;/g, function(_, url1, url2) {
        cssImports.push(url1 || url2);
        return "";
    });
    for (var imp of cssImports) {
        ret += '<link rel="stylesheet" href="' + await getMediaURL(imp, file) + '">';
    }
    return ret;
}

var CLOZE_RE = /\{\{\s*c([\d+])::([^}]+?)(?:::([^}]+?))?\s*\}\}/gm;

/***
 * Get the numbers of the clozes in a template.
 * @param {Object} model - The model object
 * @param {Object} note - The note object
 * @return {Array} - The numbers of the clozes in the template
 * */
function getClozesNumbers(model, note) {
    var numbers = [];
    var html = model.tmpls[0].qfmt;
    var fields = model.flds.map(f => f.name);
    var note_fields = note.flds.split("\x1f");
    html = html.replace(/\{\{\s*([^}]+?)\s*\}\}/g, function(match, fieldName) {
        if(fieldName.startsWith("cloze:"))
            return note_fields[fields.indexOf(fieldName.substring(6))];
    });
    html.replace(CLOZE_RE, function(_, clozeNumber) {
        if(!numbers.includes(clozeNumber))
            numbers.push(clozeNumber);
    });
    return numbers.sort((a, b) => +a - +b);
}

function makeCloze(cardNumber, html, flipped) {
    return html.replace(CLOZE_RE, function(_, clozeNumber, clozeContent, hint) {
        if (clozeNumber != cardNumber) {
            return '<span class="cloze-inactive">' + clozeContent + "</span>";
        }
        return (
            '<span class="cloze">'
            + (flipped ? clozeContent : "[" + (hint || "...") + "]")
            + "</span>"
        );
    });
}

function render(model, template, note, flipped, textOnly, noCSS) {
    var html = flipped ? template.afmt : template.qfmt;
    var fields = model.flds.map(f => f.name);
    var note_fields = note.flds.split("\x1f");
    html = html.replace(/\{\{\s*([#^])([^}]+?)\s*\}\}([\s\S]*?)\{\{\s*\/\2\s*\}\}/gm, function(_, invertSymbol, fieldName, content) {
        var invert = invertSymbol == "^";
        var ret = !!note_fields[fields.indexOf(fieldName)];
        return (invert ? !ret : ret) ? content : "";
    });
    html = html.replace(/\{\{\s*([^}]+?)\s*\}\}/g, function(match, fieldName) {
        if(fieldName.startsWith("cloze:")) {
            fieldName = fieldName.substring(6);
            var index = fields.indexOf(fieldName);
            return makeCloze(template.ord, index == -1 ? `ERROR: Field '${fieldName}' not found` : note_fields[index], flipped);
        }
        if(fieldName == "FrontSide" && flipped) {
            return render(model, template, note, false, textOnly, true);
        }
        var index = fields.indexOf(fieldName);
        return index == -1 ? `ERROR: Field '${fieldName}' not found` : note_fields[index];
    });
    return textOnly ? stripHTML(html) : (noCSS ? "" : "<style>" + model.css + "</style>") + html;
}

async function renderWithMedia(model, template, note, file, flipped) {
    return await patchMediaURLs(render(model, template, note, flipped), file);
}

var promise = Promise.resolve();

async function typeset(...elements) {
    for(var element of elements) {
        if(element.textContent.match(/\\\[.*\\\]/s)) {
            // If any of the elements contains math, call the function (which loads the script)
            return await promise.then(() => MathJax.typesetPromise(...elements));
        }
    }

    // Otherwise return a promise that resolves immediatly
    return new Promise(resolve => resolve());
}

document.addEventListener("alpine-i18n:ready", function () {
    // Setup translations
    AlpineI18n.create("en", translations);
});
