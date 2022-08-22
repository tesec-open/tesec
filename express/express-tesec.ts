// @ts-nocheck

import express from "express";

const { createHook, executionAsyncId, executionAsyncResource } = require('async_hooks');
const { trigger, triggerFile } = require('./syscall_trigger/build/Release/trigger.node');
const fs = require('fs');

var lastRequest = -1;
const headerCoro = new Map();
const typeSet = new Set();

var originalOpen = fs.open;
fs.open = (path, flags, mode, callback) => {
    var asyncId = executionAsyncId();
    if (headerCoro.has(asyncId)) {
        // fs.writeSync(1, path + " " + headerCoro.get(asyncId).toString() + "\n");
        triggerFile(Number(path.split('/').pop()), headerCoro.get(asyncId).toString());
    }
    originalOpen(path, flags, mode, callback);
};

createHook({
    init(asyncId, type, triggerAsyncId, resource) {
        if (headerCoro.has(triggerAsyncId)) {
            headerCoro.set(asyncId, headerCoro.get(triggerAsyncId))
        }
    },
    before(asyncId) {
        var data = headerCoro.get(asyncId);
        if (typeof(data) != 'undefined' && data != lastRequest) {
            trigger(data)
            lastRequest = data;
        }
    },
    destroy(asyncId) {
        if (headerCoro.has(asyncId)) {
            headerCoro.delete(asyncId);
        }
    },
    promiseResolve(asyncId) {
        var data = headerCoro.get(asyncId);
        if (typeof(data) != 'undefined' && data != lastRequest) {
            trigger(data);
            lastRequest = data;
        }
    }
}).enable();

function new_express() {
    const app = express();
    app.use((req, res, next) => {
        if ('proxy-id' in req.headers) {
            headerCoro.set(executionAsyncId(), Number(req.headers['proxy-id'].slice()))
            next();
        } else {
            res.status(400).send('Hacker!');
        }
    });
    return app
}

Object.assign(new_express, express);
exports = module.exports = new_express;

export default { new_express };
