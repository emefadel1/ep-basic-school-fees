const APP_SHELL_CACHE = "ep-basic-shell-v1";
const API_CACHE = "ep-basic-api-v1";
const IMAGE_CACHE = "ep-basic-images-v1";
const DB_NAME = "ep-basic-offline";
const REQUEST_STORE = "pending-requests";
const SYNC_TAG = "ep-basic-offline-sync";

const CORE_URLS = ["/", "/offline.html", "/manifest.json", "/icon.svg", "/icon-maskable.svg", "/favicon.svg"];
const SAFE_API_GET_PREFIXES = ["/api/v1/sessions/", "/api/v1/collections/summary/"];
const QUEUEABLE_POST_PREFIXES = ["/api/v1/collections/", "/api/v1/collections/bulk/"];

self.addEventListener("install", function onInstall(event) {
  event.waitUntil(
    caches.open(APP_SHELL_CACHE).then(function cacheCore(cache) {
      return cache.addAll(CORE_URLS);
    }).then(function finishInstall() {
      return self.skipWaiting();
    }),
  );
});

self.addEventListener("activate", function onActivate(event) {
  event.waitUntil(
    cleanupCaches().then(function claimClients() {
      return self.clients.claim();
    }),
  );
});

self.addEventListener("fetch", function onFetch(event) {
  const request = event.request;
  const url = new URL(request.url);

  if (request.method === "GET") {
    if (request.mode === "navigate") {
      event.respondWith(handleNavigationRequest(request));
      return;
    }
    if (url.origin === self.location.origin) {
      if (isStaticAssetRequest(request) === true) {
        event.respondWith(cacheFirst(request, APP_SHELL_CACHE));
        return;
      }
      if (request.destination === "image") {
        event.respondWith(cacheFirst(request, IMAGE_CACHE));
        return;
      }
      if (isSafeApiGetRequest(url) === true) {
        event.respondWith(networkFirst(request, API_CACHE));
        return;
      }
    }
    return;
  }

  if (request.method === "POST") {
    if (url.origin === self.location.origin) {
      if (shouldQueuePostRequest(url) === true) {
        event.respondWith(handleQueueablePost(request));
      }
    }
  }
});

self.addEventListener("sync", function onSync(event) {
  if (event.tag === SYNC_TAG) {
    event.waitUntil(flushQueuedRequests());
  }
});

self.addEventListener("message", function onMessage(event) {
  if (event.data === undefined) {
    return;
  }
  if (event.data.type === "OFFLINE_SYNC_NOW") {
    event.waitUntil(flushQueuedRequests());
    return;
  }
  if (event.data.type === "OFFLINE_QUEUE_UPDATED") {
    event.waitUntil(broadcastPendingCount());
  }
});

function cleanupCaches() {
  return caches.keys().then(function removeOldCaches(keys) {
    return Promise.all(
      keys.map(function removeCache(key) {
        if (key === APP_SHELL_CACHE) {
          return Promise.resolve(true);
        }
        if (key === API_CACHE) {
          return Promise.resolve(true);
        }
        if (key === IMAGE_CACHE) {
          return Promise.resolve(true);
        }
        return caches.delete(key);
      }),
    );
  });
}

function isStaticAssetRequest(request) {
  const destinations = ["script", "style", "font", "worker"];
  let index = 0;
  while (index !== destinations.length) {
    if (request.destination === destinations[index]) {
      return true;
    }
    index += 1;
  }
  return false;
}

function isSafeApiGetRequest(url) {
  let index = 0;
  while (index !== SAFE_API_GET_PREFIXES.length) {
    if (url.pathname.indexOf(SAFE_API_GET_PREFIXES[index]) === 0) {
      return true;
    }
    index += 1;
  }
  return false;
}

function shouldQueuePostRequest(url) {
  let index = 0;
  while (index !== QUEUEABLE_POST_PREFIXES.length) {
    if (url.pathname.indexOf(QUEUEABLE_POST_PREFIXES[index]) === 0) {
      return true;
    }
    index += 1;
  }
  return false;
}

function shouldStoreResponse(response) {
  if (response.ok !== true) {
    return false;
  }
  const cacheControl = response.headers.get("Cache-Control");
  if (typeof cacheControl === "string") {
    if (cacheControl.indexOf("no-store") !== -1) {
      return false;
    }
  }
  return true;
}

function cacheResponse(cacheName, request, response) {
  if (shouldStoreResponse(response) !== true) {
    return Promise.resolve(response);
  }
  return caches.open(cacheName).then(function putResponse(cache) {
    cache.put(request, response.clone());
    return response;
  });
}

function cacheFirst(request, cacheName) {
  return caches.match(request).then(function fromCache(match) {
    if (match) {
      return match;
    }
    return fetch(request).then(function fromNetwork(response) {
      return cacheResponse(cacheName, request, response);
    });
  });
}

function networkFirst(request, cacheName) {
  return fetch(request).then(function fromNetwork(response) {
    return cacheResponse(cacheName, request, response);
  }).catch(function onFailure() {
    return caches.match(request);
  });
}

function handleNavigationRequest(request) {
  return fetch(request).then(function fromNetwork(response) {
    return cacheResponse(APP_SHELL_CACHE, request, response);
  }).catch(function onFailure() {
    return caches.match(request).then(function cachedNavigation(match) {
      if (match) {
        return match;
      }
      return caches.match("/").then(function cachedRoot(root) {
        if (root) {
          return root;
        }
        return caches.match("/offline.html");
      });
    });
  });
}
function openQueueDatabase() {
  return new Promise(function open(resolve, reject) {
    const request = indexedDB.open(DB_NAME, 1);
    request.onupgradeneeded = function onUpgrade(event) {
      const db = event.target.result;
      if (db.objectStoreNames.contains(REQUEST_STORE) === false) {
        const store = db.createObjectStore(REQUEST_STORE, { keyPath: "id" });
        store.createIndex("createdAt", "createdAt");
      }
    };
    request.onsuccess = function onSuccess() {
      resolve(request.result);
    };
    request.onerror = function onError() {
      reject(request.error ? request.error : new Error("Could not open offline queue."));
    };
  });
}

function getQueuedRequests() {
  return openQueueDatabase().then(function getAll(db) {
    return new Promise(function read(resolve, reject) {
      const transaction = db.transaction(REQUEST_STORE, "readonly");
      const request = transaction.objectStore(REQUEST_STORE).getAll();
      request.onsuccess = function onSuccess() {
        resolve(request.result ? request.result : []);
      };
      request.onerror = function onError() {
        reject(request.error ? request.error : new Error("Could not read queued requests."));
      };
    });
  });
}

function countQueuedRequests() {
  return openQueueDatabase().then(function countAll(db) {
    return new Promise(function read(resolve, reject) {
      const transaction = db.transaction(REQUEST_STORE, "readonly");
      const request = transaction.objectStore(REQUEST_STORE).count();
      request.onsuccess = function onSuccess() {
        resolve(request.result ? request.result : 0);
      };
      request.onerror = function onError() {
        reject(request.error ? request.error : new Error("Could not count queued requests."));
      };
    });
  });
}

function saveQueuedRequest(record) {
  return openQueueDatabase().then(function save(db) {
    return new Promise(function write(resolve, reject) {
      const transaction = db.transaction(REQUEST_STORE, "readwrite");
      transaction.objectStore(REQUEST_STORE).put(record);
      transaction.oncomplete = function onComplete() {
        resolve(record);
      };
      transaction.onerror = function onError() {
        reject(transaction.error ? transaction.error : new Error("Could not save queued request."));
      };
    });
  });
}

function deleteQueuedRequest(id) {
  return openQueueDatabase().then(function remove(db) {
    return new Promise(function write(resolve, reject) {
      const transaction = db.transaction(REQUEST_STORE, "readwrite");
      transaction.objectStore(REQUEST_STORE).delete(id);
      transaction.oncomplete = function onComplete() {
        resolve(true);
      };
      transaction.onerror = function onError() {
        reject(transaction.error ? transaction.error : new Error("Could not remove queued request."));
      };
    });
  });
}

function serialiseRequest(request) {
  const headers = {};
  request.headers.forEach(function copyHeader(value, key) {
    if (key === "authorization") {
      headers[key] = value;
      return;
    }
    if (key === "content-type") {
      headers[key] = value;
      return;
    }
    if (key === "accept") {
      headers[key] = value;
    }
  });
  return request.clone().text().then(function withBody(bodyText) {
    return {
      id: "offline-" + String(Date.now()) + "-" + String(Math.random()).slice(2),
      url: request.url,
      method: request.method,
      headers: headers,
      body: bodyText ? bodyText : null,
      credentials: request.credentials ? request.credentials : "include",
      createdAt: new Date().toISOString(),
    };
  }).catch(function onFailure() {
    return {
      id: "offline-" + String(Date.now()) + "-" + String(Math.random()).slice(2),
      url: request.url,
      method: request.method,
      headers: headers,
      body: null,
      credentials: request.credentials ? request.credentials : "include",
      createdAt: new Date().toISOString(),
    };
  });
}
function jsonResponse(payload, statusCode) {
  return new Response(JSON.stringify(payload), {
    status: statusCode,
    headers: { "Content-Type": "application/json" },
  });
}

function registerBackgroundSync() {
  if (self.registration.sync === undefined) {
    return Promise.resolve(false);
  }
  return self.registration.sync.register(SYNC_TAG).then(function onSuccess() {
    return true;
  }).catch(function onFailure() {
    return false;
  });
}

function notifyClients(message) {
  return self.clients.matchAll({ type: "window", includeUncontrolled: true }).then(function send(clients) {
    clients.forEach(function notify(client) {
      client.postMessage(message);
    });
  });
}

function broadcastPendingCount() {
  return countQueuedRequests().then(function withCount(pendingCount) {
    return notifyClients({ type: "OFFLINE_QUEUE_UPDATED", pendingCount: pendingCount });
  });
}

function handleQueueablePost(request) {
  return fetch(request.clone()).catch(function onFailure() {
    return serialiseRequest(request).then(function queueRecord(record) {
      return saveQueuedRequest(record).then(function afterSave() {
        return registerBackgroundSync().then(function afterRegister() {
          return broadcastPendingCount().then(function afterBroadcast() {
            return jsonResponse({ success: false, queued: true, offline: true, message: "Request saved for sync when the network returns." }, 202);
          });
        });
      });
    });
  });
}

function flushQueuedRequests() {
  return notifyClients({ type: "OFFLINE_SYNC_STARTED" }).then(function begin() {
    return getQueuedRequests().then(async function syncItems(items) {
      let synced = 0;
      let index = 0;
      while (index !== items.length) {
        const item = items[index];
        try {
          const init = {
            method: item.method,
            headers: item.headers ? item.headers : {},
            credentials: item.credentials ? item.credentials : "include",
          };
          if (item.body !== null) {
            init.body = item.body;
          }
          const response = await fetch(item.url, init);
          if (response.ok === true) {
            await deleteQueuedRequest(item.id);
            synced += 1;
          }
        } catch (error) {
        }
        index += 1;
      }
      const pendingCount = await countQueuedRequests();
      const lastSyncAt = new Date().toISOString();
      return notifyClients({ type: "OFFLINE_SYNC_COMPLETED", synced: synced, pendingCount: pendingCount, lastSyncAt: lastSyncAt });
    });
  }).catch(function onError() {
    return notifyClients({ type: "OFFLINE_SYNC_FAILED" });
  });
}
