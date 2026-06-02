const assert = require("assert");
const fs = require("fs");
const path = require("path");
const vm = require("vm");

function makeEntries(count) {
    return Array.from({ length: count }, (_, index) => ({
        number: index + 1,
        name: `racer_${index + 1}`,
    }));
}

function loadWidget() {
    const file = path.join(__dirname, "..", "entries-widget-1col.html");
    const html = fs.readFileSync(file, "utf8");
    const script = html.match(/<script>([\s\S]*)<\/script>/)[1];
    const elements = new Map();

    function getElement(id) {
        if (!elements.has(id)) {
            elements.set(id, {
                id,
                innerHTML: "",
                textContent: "",
                className: "",
                style: {},
                appendChild() {},
                parentNode: {
                    replaceChild(fresh, old) {
                        elements.set(old.id, fresh);
                    },
                },
                cloneNode() {
                    return getElement(id);
                },
            });
        }
        return elements.get(id);
    }

    const context = {
        document: {
            getElementById: getElement,
            createElement: () => ({ className: "", style: {}, appendChild() {} }),
        },
        WebSocket: function WebSocket(url) {
            this.url = url;
            this.send = () => {};
        },
        setInterval: () => 1,
        clearInterval: () => {},
        setTimeout: () => 1,
        Math,
        JSON,
        String,
        Array,
    };

    vm.createContext(context);
    vm.runInContext(script, context);

    return {
        message(entries) {
            vm.runInContext(
                `ws.onmessage({ data: ${JSON.stringify(JSON.stringify(entries))} });`,
                context
            );
        },
        pageLabel() {
            return getElement("page-label").textContent;
        },
        gridHtml() {
            return getElement("grid").innerHTML;
        },
    };
}

const widget = loadWidget();
widget.message(makeEntries(16));
widget.message(makeEntries(17));

assert.strictEqual(widget.pageLabel(), "PAGE 2 / 2");
assert.match(widget.gridHtml(), /racer_17/i);
