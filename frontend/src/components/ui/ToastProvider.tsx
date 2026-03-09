import React from "react";

const ToastContext = React.createContext(undefined as any);

const TONE_STYLES: any = {
  info: "border-slate-200 bg-white text-slate-800",
  success: "border-emerald-200 bg-emerald-50 text-emerald-900",
  warning: "border-amber-200 bg-amber-50 text-amber-900",
  error: "border-rose-200 bg-rose-50 text-rose-900",
};

export function ToastProvider(props: any) {
  const [toasts, setToasts] = React.useState([] as any);

  const removeToast = React.useCallback(function removeToast(id: string) {
    setToasts(function update(current: any) {
      return current.filter(function keepToast(item: any) {
        return item.id !== id;
      });
    });
  }, []);

  const pushToast = React.useCallback(function pushToast(input: any) {
    let title = "Notice";
    let tone = "info";
    if (typeof input.title === "string") {
      title = input.title;
    }
    if (typeof input.tone === "string") {
      tone = input.tone;
    }
    const next = {
      id: String(Date.now()) + "-" + String(Math.random()).slice(2),
      title: title,
      description: input.description,
      tone: tone,
    };
    setToasts(function update(current: any) {
      return current.concat([next]);
    });
    return next.id;
  }, []);

  React.useEffect(function manageTimeouts() {
    if (toasts.length === 0) {
      return undefined;
    }
    const timers = toasts.map(function schedule(toast: any) {
      return window.setTimeout(function dismissToast() {
        removeToast(toast.id);
      }, 4000);
    });
    return function cleanup() {
      timers.forEach(function clearTimer(timer: any) {
        window.clearTimeout(timer);
      });
    };
  }, [removeToast, toasts]);

  const viewport = React.createElement(
    "div",
    {
      className: "pointer-events-none fixed right-4 top-4 z-50 flex w-full max-w-sm flex-col gap-3",
    },
    toasts.map(function renderToast(toast: any) {
      const toneClass = TONE_STYLES[toast.tone] ? TONE_STYLES[toast.tone] : TONE_STYLES.info;
      const children = [
        React.createElement("div", { key: "title", className: "text-sm font-semibold" }, toast.title),
      ];
      if (toast.description) {
        children.push(React.createElement("div", { key: "description", className: "mt-1 text-sm opacity-90" }, toast.description));
      }
      children.push(
        React.createElement(
          "button",
          {
            key: "dismiss",
            type: "button",
            className: "mt-3 text-xs font-medium uppercase tracking-wide",
            onClick: function onClick() {
              removeToast(toast.id);
            },
          },
          "Dismiss",
        ),
      );
      return React.createElement(
        "div",
        {
          key: toast.id,
          className: "pointer-events-auto rounded-2xl border px-4 py-3 shadow-lg " + toneClass,
        },
        children,
      );
    }),
  );

  return React.createElement(
    ToastContext.Provider,
    { value: { pushToast: pushToast, removeToast: removeToast } },
    [props.children, viewport],
  );
}

export function useToast() {
  const context = React.useContext(ToastContext);
  if (context === undefined) {
    throw new Error("useToast must be used inside ToastProvider.");
  }
  return context;
}
