import React from "react";

export default function NotificationBell(props: any) {
  let count = 0;
  if (typeof props.count === "number") {
    count = props.count;
  }
  const children = [
    React.createElement("span", { key: "icon", className: "text-lg" }, "Bell"),
  ];
  if (count !== 0) {
    children.push(
      React.createElement(
        "span",
        {
          key: "count",
          className: "rounded-full bg-slate-900 px-2 py-0.5 text-xs font-semibold text-white",
        },
        String(count),
      ),
    );
  }

  return React.createElement(
    "button",
    {
      type: "button",
      className: "inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 shadow-sm",
      onClick: props.onClick,
    },
    children,
  );
}
