mkdir -p static/ext
curl -sL https://cdn.jsdelivr.net/npm/alpinejs@3/dist/cdn.min.js > static/ext/cdn.min.js
curl -sL https://cdn.jsdelivr.net/npm/alpinejs-i18n@2/dist/cdn.min.js > static/ext/i18n.min.js
curl -sL https://cdn.jsdelivr.net/npm/eruda@3/eruda.min.js > static/ext/eruda.min.js
curl -sL https://cdn.jsdelivr.net/npm/jszip@3/dist/jszip.min.js > static/ext/jszip.min.js
curl -sL https://cdn.jsdelivr.net/npm/sql.js@1/dist/sql-wasm.js > static/ext/sql-wasm.js
curl -sL https://cdn.jsdelivr.net/npm/sql.js@1/dist/sql-wasm.wasm > static/ext/sql-wasm.wasm
curl -sL https://cdn.jsdelivr.net/npm/tablesort@5/dist/tablesort.min.js > static/ext/tablesort.min.js
