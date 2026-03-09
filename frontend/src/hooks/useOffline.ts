import React from "react";
import { clearPendingRequests, countPendingRequests, getLastSyncAt, replayPendingRequests, savePendingRequest, setLastSyncAt } from "@/lib/offlineDB";

const QUEUEABLE_ROUTES = ["/api/v1/collections/", "/api/v1/collections/bulk/"];

function postServiceWorkerMessage(message: any) {
  if (typeof navigator === "undefined") {
    return;
  }
  if (navigator.serviceWorker === undefined) {
    return;
  }
  if (navigator.serviceWorker.controller === null) {
    return;
  }
  navigator.serviceWorker.controller.postMessage(message);
}

export function shouldQueueOfflineRequest(input: any) {
  const method = input.method ? String(input.method).toUpperCase() : "GET";
  if (method !== "POST") {
    return false;
  }
  if (typeof input.url !== "string") {
    return false;
  }
  let index = 0;
  while (index !== QUEUEABLE_ROUTES.length) {
    if (input.url.indexOf(QUEUEABLE_ROUTES[index]) !== -1) {
      return true;
    }
    index += 1;
  }
  return false;
}

export async function saveOffline(input: any) {
  if (shouldQueueOfflineRequest(input) === false) {
    throw new Error("This request is not configured for offline queueing.");
  }
  const record = await savePendingRequest(input);
  postServiceWorkerMessage({ type: "OFFLINE_QUEUE_UPDATED" });
  return record;
}

export function useOffline() {
  const [isOnline, setIsOnline] = React.useState(true);
  const [pendingCount, setPendingCount] = React.useState(0);
  const [isSyncing, setIsSyncing] = React.useState(false);
  const [lastSyncAt, setLastSyncState] = React.useState(null as any);

  const refresh = React.useCallback(async function refresh() {
    const pending = await countPendingRequests();
    setPendingCount(Number(pending));
    const lastSync = await getLastSyncAt();
    setLastSyncState(lastSync);
  }, []);

  React.useEffect(function bindStatus() {
    if (typeof window === "undefined") {
      return undefined;
    }
    setIsOnline(window.navigator.onLine);
    refresh();
    function markOnline() {
      setIsOnline(true);
      refresh();
    }
    function markOffline() {
      setIsOnline(false);
    }
    function onMessage(event: any) {
      if (event.data === undefined) {
        return;
      }
      if (event.data.type === "OFFLINE_QUEUE_UPDATED") {
        refresh();
        return;
      }
      if (event.data.type === "OFFLINE_SYNC_STARTED") {
        setIsSyncing(true);
        return;
      }
      if (event.data.type === "OFFLINE_SYNC_COMPLETED") {
        setIsSyncing(false);
        if (event.data.lastSyncAt) {
          setLastSyncState(event.data.lastSyncAt);
        }
        refresh();
        return;
      }
      if (event.data.type === "OFFLINE_SYNC_FAILED") {
        setIsSyncing(false);
        refresh();
      }
    }
    window.addEventListener("online", markOnline);
    window.addEventListener("offline", markOffline);
    if (navigator.serviceWorker !== undefined) {
      navigator.serviceWorker.addEventListener("message", onMessage);
    }
    return function cleanup() {
      window.removeEventListener("online", markOnline);
      window.removeEventListener("offline", markOffline);
      if (navigator.serviceWorker !== undefined) {
        navigator.serviceWorker.removeEventListener("message", onMessage);
      }
    };
  }, [refresh]);

  const syncNow = React.useCallback(async function syncNow() {
    if (typeof navigator !== "undefined") {
      if (navigator.onLine === false) {
        return { total: pendingCount, synced: 0, remaining: pendingCount };
      }
    }
    setIsSyncing(true);
    postServiceWorkerMessage({ type: "OFFLINE_SYNC_NOW" });
    const result = await replayPendingRequests();
    if (result.synced !== 0) {
      const timestamp = new Date().toISOString();
      await setLastSyncAt(timestamp);
      setLastSyncState(timestamp);
    }
    setIsSyncing(false);
    await refresh();
    return result;
  }, [pendingCount, refresh]);

  const clearPending = React.useCallback(async function clearPending() {
    await clearPendingRequests();
    await refresh();
    postServiceWorkerMessage({ type: "OFFLINE_QUEUE_UPDATED" });
  }, [refresh]);

  const saveOfflineAction = React.useCallback(async function saveOfflineAction(input: any) {
    const record = await saveOffline(input);
    await refresh();
    return record;
  }, [refresh]);

  return {
    isOnline: isOnline,
    pendingCount: pendingCount,
    isSyncing: isSyncing,
    lastSyncAt: lastSyncAt,
    refresh: refresh,
    saveOffline: saveOfflineAction,
    syncNow: syncNow,
    clearPending: clearPending,
  };
}

export function OfflineStatusBanner() {
  const offline = useOffline();

  if (offline.isOnline === true) {
    if (offline.pendingCount === 0) {
      if (offline.isSyncing === false) {
        return null;
      }
    }
  }

  let title = "Offline mode active";
  let body = "The app shell is available. New queueable submissions can wait until you reconnect.";
  if (offline.isOnline === true) {
    title = "Pending sync available";
    body = "You are back online. Review the queued submissions below and sync them when ready.";
  }
  if (offline.isSyncing === true) {
    title = "Syncing queued work";
    body = "Queued submissions are being replayed to the server now.";
  }

  const meta = [];
  if (offline.pendingCount !== 0) {
    meta.push(React.createElement("span", { key: "count", className: "rounded-full bg-slate-900 px-3 py-1 text-xs font-semibold text-white" }, String(offline.pendingCount) + " pending"));
  }
  if (typeof offline.lastSyncAt === "string") {
    meta.push(React.createElement("span", { key: "time", className: "text-xs text-slate-600" }, "Last sync: " + new Date(offline.lastSyncAt).toLocaleString()));
  }

  const actions = [];
  if (offline.isOnline === true) {
    if (offline.pendingCount !== 0) {
      actions.push(React.createElement("button", { key: "sync", type: "button", className: "rounded-full bg-slate-900 px-4 py-2 text-sm font-semibold text-white", onClick: function onClick() { offline.syncNow(); }, disabled: offline.isSyncing === true }, offline.isSyncing === true ? "Syncing..." : "Sync now"));
      actions.push(React.createElement("button", { key: "clear", type: "button", className: "rounded-full bg-slate-200 px-4 py-2 text-sm font-semibold text-slate-800", onClick: function onClick() { offline.clearPending(); }, disabled: offline.isSyncing === true }, "Clear pending"));
    }
  }

  return React.createElement(
    "div",
    { className: "border-b border-amber-200 bg-amber-50 px-4 py-3 text-slate-900" },
    React.createElement(
      "div",
      { className: "mx-auto flex max-w-7xl flex-col gap-3 lg:flex-row lg:items-center lg:justify-between" },
      [
        React.createElement(
          "div",
          { key: "copy" },
          [
            React.createElement("div", { key: "title", className: "text-sm font-semibold" }, title),
            React.createElement("div", { key: "body", className: "mt-1 text-sm text-slate-700" }, body),
            meta.length !== 0 ? React.createElement("div", { key: "meta", className: "mt-2 flex flex-wrap gap-2" }, meta) : null,
          ],
        ),
        actions.length !== 0 ? React.createElement("div", { key: "actions", className: "flex flex-wrap gap-2" }, actions) : null,
      ],
    ),
  );
}
