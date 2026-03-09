export const OFFLINE_DB_NAME = "ep-basic-offline";
export const OFFLINE_REQUEST_STORE = "pending-requests";
export const OFFLINE_META_STORE = "meta";

export interface OfflineRequestRecord {
  id: string;
  url: string;
  method: string;
  headers: any;
  body: any;
  credentials?: RequestCredentials;
  createdAt: string;
}

function openDatabase() {
  return new Promise(function open(resolve, reject) {
    if (typeof window === "undefined") {
      resolve(null);
      return;
    }
    if (window.indexedDB === undefined) {
      resolve(null);
      return;
    }
    const request = window.indexedDB.open(OFFLINE_DB_NAME, 1);
    request.onupgradeneeded = function onUpgrade(event: any) {
      const db = event.target.result;
      if (db.objectStoreNames.contains(OFFLINE_REQUEST_STORE) === false) {
        const store = db.createObjectStore(OFFLINE_REQUEST_STORE, { keyPath: "id" });
        store.createIndex("createdAt", "createdAt");
      }
      if (db.objectStoreNames.contains(OFFLINE_META_STORE) === false) {
        db.createObjectStore(OFFLINE_META_STORE, { keyPath: "key" });
      }
    };
    request.onsuccess = function onSuccess() {
      resolve(request.result);
    };
    request.onerror = function onError() {
      reject(request.error ? request.error : new Error("Could not open offline database."));
    };
  });
}

function nextRequestId() {
  return "offline-" + String(Date.now()) + "-" + String(Math.random()).slice(2);
}

export function buildOfflineRequest(input: any) {
  const headers = input.headers ? input.headers : {};
  let body = null;
  if (typeof input.body === "string") {
    body = input.body;
  }
  return {
    id: input.id ? input.id : nextRequestId(),
    url: input.url,
    method: input.method ? String(input.method).toUpperCase() : "POST",
    headers: headers,
    body: body,
    credentials: input.credentials ? input.credentials : "include",
    createdAt: input.createdAt ? input.createdAt : new Date().toISOString(),
  };
}

export async function savePendingRequest(input: any) {
  const record = buildOfflineRequest(input);
  const db: any = await openDatabase();
  if (db === null) {
    return record;
  }
  await new Promise(function write(resolve, reject) {
    const transaction = db.transaction(OFFLINE_REQUEST_STORE, "readwrite");
    transaction.objectStore(OFFLINE_REQUEST_STORE).put(record);
    transaction.oncomplete = function onComplete() {
      resolve(record);
    };
    transaction.onerror = function onError() {
      reject(transaction.error ? transaction.error : new Error("Could not save pending request."));
    };
  });
  return record;
}

export async function getPendingRequests() {
  const db: any = await openDatabase();
  if (db === null) {
    return [];
  }
  return new Promise(function read(resolve, reject) {
    const transaction = db.transaction(OFFLINE_REQUEST_STORE, "readonly");
    const request = transaction.objectStore(OFFLINE_REQUEST_STORE).getAll();
    request.onsuccess = function onSuccess() {
      resolve(request.result ? request.result : []);
    };
    request.onerror = function onError() {
      reject(request.error ? request.error : new Error("Could not read pending requests."));
    };
  });
}

export async function countPendingRequests() {
  const db: any = await openDatabase();
  if (db === null) {
    return 0;
  }
  return new Promise(function count(resolve, reject) {
    const transaction = db.transaction(OFFLINE_REQUEST_STORE, "readonly");
    const request = transaction.objectStore(OFFLINE_REQUEST_STORE).count();
    request.onsuccess = function onSuccess() {
      resolve(request.result ? request.result : 0);
    };
    request.onerror = function onError() {
      reject(request.error ? request.error : new Error("Could not count pending requests."));
    };
  });
}

export async function deletePendingRequest(id: string) {
  const db: any = await openDatabase();
  if (db === null) {
    return;
  }
  await new Promise(function remove(resolve, reject) {
    const transaction = db.transaction(OFFLINE_REQUEST_STORE, "readwrite");
    transaction.objectStore(OFFLINE_REQUEST_STORE).delete(id);
    transaction.oncomplete = function onComplete() {
      resolve(true);
    };
    transaction.onerror = function onError() {
      reject(transaction.error ? transaction.error : new Error("Could not delete pending request."));
    };
  });
}

export async function clearPendingRequests() {
  const db: any = await openDatabase();
  if (db === null) {
    return;
  }
  await new Promise(function clear(resolve, reject) {
    const transaction = db.transaction(OFFLINE_REQUEST_STORE, "readwrite");
    transaction.objectStore(OFFLINE_REQUEST_STORE).clear();
    transaction.oncomplete = function onComplete() {
      resolve(true);
    };
    transaction.onerror = function onError() {
      reject(transaction.error ? transaction.error : new Error("Could not clear pending requests."));
    };
  });
}

export async function setOfflineMeta(key: string, value: any) {
  const db: any = await openDatabase();
  if (db === null) {
    return value;
  }
  await new Promise(function write(resolve, reject) {
    const transaction = db.transaction(OFFLINE_META_STORE, "readwrite");
    transaction.objectStore(OFFLINE_META_STORE).put({ key: key, value: value });
    transaction.oncomplete = function onComplete() {
      resolve(true);
    };
    transaction.onerror = function onError() {
      reject(transaction.error ? transaction.error : new Error("Could not store offline metadata."));
    };
  });
  return value;
}

export async function getOfflineMeta(key: string) {
  const db: any = await openDatabase();
  if (db === null) {
    return null;
  }
  return new Promise(function read(resolve, reject) {
    const transaction = db.transaction(OFFLINE_META_STORE, "readonly");
    const request = transaction.objectStore(OFFLINE_META_STORE).get(key);
    request.onsuccess = function onSuccess() {
      if (request.result === undefined) {
        resolve(null);
        return;
      }
      resolve(request.result.value);
    };
    request.onerror = function onError() {
      reject(request.error ? request.error : new Error("Could not read offline metadata."));
    };
  });
}

export async function setLastSyncAt(value: string) {
  return setOfflineMeta("last-sync-at", value);
}

export async function getLastSyncAt() {
  return getOfflineMeta("last-sync-at");
}

export async function replayPendingRequests() {
  const items: any = await getPendingRequests();
  let synced = 0;
  let index = 0;
  while (index !== items.length) {
    const item = items[index];
    try {
      const init: any = {
        method: item.method,
        credentials: item.credentials ? item.credentials : "include",
        headers: item.headers ? item.headers : {},
      };
      if (item.body !== null) {
        init.body = item.body;
      }
      const response = await fetch(item.url, init);
      if (response.ok === true) {
        await deletePendingRequest(item.id);
        synced += 1;
      }
    } catch (error) {
    }
    index += 1;
  }
  if (synced !== 0) {
    await setLastSyncAt(new Date().toISOString());
  }
  const remaining = await countPendingRequests();
  return { total: items.length, synced: synced, remaining: remaining };
}
