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
                if(node.tagName == "TABLE") {
                    new Tablesort(node);
                }
            }
        }
    });
    observer.observe(document.body, {childList: true, subtree: true})
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

async function openFile(input) {
    var jszip = new JSZip();
    var zip = await jszip.loadAsync(input.files[0]);
    var buf = await zip.file("collection.anki21").async("uint8array");

    var media = await zip.file("media").async("text");

    var SQL = await initSqlJs({locateFile: f => "static/" + f});
    var db = new SQL.Database(buf);

    var col_info = sqlToDict(db.exec("SELECT models, decks FROM col"))[0];
    // https://stackoverflow.com/a/8161801
    // https://dba.stackexchange.com/a/315294
    var notes = sqlToDict(db.exec("SELECT notes.mid, notes.mod, notes.tags, notes.flds, notes.sfld, cards.did FROM notes LEFT JOIN cards ON notes.id = cards.nid AND cards.id = (SELECT id FROM cards WHERE notes.id = cards.nid LIMIT 1)"));
    return [
        input.value.split(/(\\|\/)/g).pop(),
        {
            models: JSON.parse(col_info.models),
            decks: JSON.parse(col_info.decks),
            notes: notes,
            media: JSON.parse(media),
            zip: zip,
        },
    ];
}

function getDeck(file, deckId) {
    return file.notes.filter(e => e.did == +deckId);
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
        return stripHTML(render(file.models[note.mid], 0, note, false, true));
    if(field == "answer")
        return stripHTML(render(file.models[note.mid], 0, note, true, true));
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
    var parts = html.split(/(<img[^>]+src=")([^"]+)("[^>]*>)/g);
    // [before_tag, before, url, after, ...]
    var ret = "";
    for(var i = 0, l = parts.length; i < l; i++) {
        if(i % 4 == 2)  // URL
            ret += await getMediaURL(parts[i], file);
        else  // normal text
            ret += parts[i];
    }
    return ret;
}

function render(model, id, note, flipped, textOnly) {
    var html = flipped ? model.tmpls[id].afmt : model.tmpls[id].qfmt;
    var fields = model.flds.map(f => f.name);
    var note_fields = note.flds.split("\x1f");
    html = html.replace(/\{\{\s*([^}]+?)\s*\}\}/g, function(_, param) {
        if(param == "FrontSide" && flipped) {
            return render(model, id, note, false, textOnly);
        }
        return note_fields[fields.indexOf(param)];
    });
    return textOnly ? stripHTML(html) : "<style>" + model.css + "</style>" + html;
}

async function renderWithMedia(model, id, note, file, flipped) {
    return await patchMediaURLs(render(model, id, note, flipped), file);
}
