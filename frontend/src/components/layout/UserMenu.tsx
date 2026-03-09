import React from "react";
import { Link } from "react-router-dom";

export default function UserMenu(props: any) {
  const [open, setOpen] = React.useState(false);

  let initials = "US";
  if (typeof props.fullName === "string") {
    const derived = props.fullName.split(" ").map(function takeInitial(part: string) { return part.slice(0, 1); }).join("").slice(0, 2).toUpperCase();
    if (derived !== "") {
      initials = derived;
    }
  }

  let displayName = "School User";
  if (typeof props.fullName === "string") {
    displayName = props.fullName;
  }

  let displayRole = "Role";
  if (typeof props.roleLabel === "string") {
    displayRole = props.roleLabel;
  }

  const menuChildren: any[] = [];
  if (props.showSettings === true) {
    menuChildren.push(
      React.createElement(
        Link,
        {
          key: "settings",
          to: "/settings",
          className: "block rounded-xl px-3 py-2 text-sm text-slate-700 hover:bg-slate-100",
          onClick: function onClick() {
            setOpen(false);
          },
        },
        "Settings",
      ),
    );
  }
  menuChildren.push(
    React.createElement(
      "button",
      {
        key: "logout",
        type: "button",
        className: "block w-full rounded-xl px-3 py-2 text-left text-sm text-rose-700 hover:bg-rose-50",
        onClick: function onClick() {
          setOpen(false);
          if (props.onLogout) {
            props.onLogout();
          }
        },
      },
      "Sign out",
    ),
  );

  const menu = open === true
    ? React.createElement(
        "div",
        {
          className: "absolute right-0 top-14 z-40 w-52 rounded-2xl border border-slate-200 bg-white p-2 shadow-xl",
        },
        menuChildren,
      )
    : null;

  return React.createElement(
    "div",
    { className: "relative" },
    [
      React.createElement(
        "button",
        {
          key: "trigger",
          type: "button",
          className: "inline-flex items-center gap-3 rounded-full border border-slate-200 bg-white px-3 py-2 text-left shadow-sm",
          onClick: function onClick() {
            setOpen(open === false);
          },
        },
        [
          React.createElement(
            "span",
            {
              key: "avatar",
              className: "flex h-9 w-9 items-center justify-center rounded-full bg-slate-900 text-xs font-semibold text-white",
            },
            initials,
          ),
          React.createElement(
            "span",
            { key: "meta", className: "hidden text-sm sm:block" },
            [
              React.createElement("div", { key: "name", className: "font-medium text-slate-900" }, displayName),
              React.createElement("div", { key: "role", className: "text-xs text-slate-500" }, displayRole),
            ],
          ),
        ],
      ),
      menu,
    ],
  );
}
