import React from "react";
import { Link } from "react-router-dom";

export default function PlaceholderPage(props: any) {
  let title = "Coming soon";
  if (typeof props.title === "string") {
    title = props.title;
  }

  let description = "This section is connected to the app shell and ready for the next feature step.";
  if (typeof props.description === "string") {
    description = props.description;
  }

  const actions = Array.isArray(props.actions) ? props.actions : [];
  const actionLinks = actions.map(function renderAction(action: any, index: number) {
    return React.createElement(
      Link,
      {
        key: String(index),
        to: action.to,
        className: "inline-flex items-center rounded-full bg-slate-900 px-4 py-2 text-sm font-medium text-white shadow-sm",
      },
      action.label,
    );
  });

  const children = [
    React.createElement(
      "div",
      { key: "eyebrow", className: "text-xs font-semibold uppercase tracking-widest text-slate-500" },
      "Workspace foundation",
    ),
    React.createElement("h1", { key: "title", className: "mt-3 text-3xl font-semibold text-slate-900" }, title),
    React.createElement("p", { key: "description", className: "mt-3 max-w-2xl text-sm text-slate-600" }, description),
  ];

  if (actionLinks.length !== 0) {
    children.push(
      React.createElement(
        "div",
        { key: "actions", className: "mt-6 flex flex-wrap gap-3" },
        actionLinks,
      ),
    );
  }

  return React.createElement(
    "div",
    { className: "rounded-3xl border border-slate-200 bg-white p-8 shadow-sm" },
    children,
  );
}
