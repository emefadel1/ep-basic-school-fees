import React from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import NotificationBell from "@/components/layout/NotificationBell";
import OfflineBanner from "@/components/layout/OfflineBanner";
import UserMenu from "@/components/layout/UserMenu";
import { APP_ROLES, roleLabel } from "@/lib/auth";

const NAV_ITEMS = [
  { to: "/dashboard", label: "Dashboard", roles: APP_ROLES },
  { to: "/fees", label: "Fees", roles: ["TEACHER", "CONTACT_PERSON", "HEADTEACHER", "BURSAR"] },
  { to: "/sessions", label: "Sessions", roles: ["HEADTEACHER", "BURSAR"] },
  { to: "/reports", label: "Reports", roles: ["CONTACT_PERSON", "HEADTEACHER", "BURSAR", "BOARD"] },
  { to: "/students", label: "Students", roles: ["TEACHER", "CONTACT_PERSON", "HEADTEACHER", "BURSAR"] },
  { to: "/staff", label: "Staff", roles: ["HEADTEACHER", "BURSAR", "BOARD"] },
  { to: "/audit", label: "Audit", roles: ["BURSAR"] },
  { to: "/settings", label: "Settings", roles: ["HEADTEACHER", "BURSAR"] },
];

function linkClass(state: any) {
  let classes = "flex items-center rounded-2xl px-4 py-3 text-sm font-medium transition ";
  if (state.isActive === true) {
    classes += "bg-slate-900 text-white shadow-lg shadow-slate-300";
  } else {
    classes += "text-slate-600 hover:bg-slate-200";
  }
  return classes;
}

function getPageTitle(pathname: string) {
  if (pathname.indexOf("/fees") === 0) {
    return "Fee collection";
  }
  if (pathname.indexOf("/sessions") === 0) {
    return "Sessions";
  }
  if (pathname.indexOf("/reports") === 0) {
    return "Reports";
  }
  if (pathname.indexOf("/students") === 0) {
    return "Students";
  }
  if (pathname.indexOf("/staff") === 0) {
    return "Staff";
  }
  if (pathname.indexOf("/audit") === 0) {
    return "Audit and compliance";
  }
  if (pathname.indexOf("/settings") === 0) {
    return "Settings";
  }
  return "Dashboard";
}

export default function DashboardLayout() {
  const auth = useAuth();
  const location = useLocation();
  const [mobileOpen, setMobileOpen] = React.useState(false);

  React.useEffect(function closeMenuOnNavigation() {
    setMobileOpen(false);
  }, [location.pathname]);

  let role = null;
  let fullName = "School User";
  if (auth.user !== null) {
    role = auth.user.role;
    fullName = auth.user.full_name ? auth.user.full_name : auth.user.username;
  }

  const visibleItems = NAV_ITEMS.filter(function filterNav(item: any) {
    if (role === null) {
      return false;
    }
    return item.roles.indexOf(role) !== -1;
  });

  let sidebarClass = "fixed inset-y-0 left-0 z-40 w-72 border-r border-slate-200 bg-white px-5 py-6 shadow-2xl transition-transform lg:static lg:translate-x-0 lg:shadow-none ";
  if (mobileOpen === true) {
    sidebarClass += "translate-x-0";
  } else {
    sidebarClass += "-translate-x-full";
  }

  const sidebar = React.createElement(
    "aside",
    { className: sidebarClass },
    [
      React.createElement(
        "div",
        { key: "brand", className: "border-b border-slate-200 pb-5" },
        [
          React.createElement("div", { key: "eyebrow", className: "text-xs font-semibold uppercase tracking-[0.3em] text-slate-500" }, "School fees"),
          React.createElement("div", { key: "name", className: "mt-3 text-2xl font-semibold text-slate-900" }, "E.P Basic School"),
          React.createElement("div", { key: "role", className: "mt-3 inline-flex rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-600" }, roleLabel(role)),
        ],
      ),
      React.createElement(
        "nav",
        { key: "nav", className: "mt-6 space-y-2" },
        visibleItems.map(function renderItem(item: any) {
          return React.createElement(NavLink, { key: item.to, to: item.to, className: linkClass }, item.label);
        }),
      ),
      React.createElement(
        "div",
        { key: "support", className: "mt-8 rounded-3xl bg-slate-900 p-5 text-slate-100" },
        [
          React.createElement("div", { key: "title", className: "text-sm font-semibold" }, "Shared shell ready"),
          React.createElement("p", { key: "body", className: "mt-2 text-sm text-slate-300" }, "Routing, auth guards, offline status, and role-aware navigation are now in place."),
        ],
      ),
    ],
  );

  const overlay = mobileOpen === true
    ? React.createElement("button", { type: "button", className: "fixed inset-0 z-30 bg-slate-950/40 lg:hidden", onClick: function onClick() { setMobileOpen(false); } })
    : null;

  const header = React.createElement(
    "header",
    { className: "sticky top-0 z-20 border-b border-slate-200 bg-slate-100/90 px-4 py-4 backdrop-blur sm:px-6 lg:px-8" },
    React.createElement(
      "div",
      { className: "flex items-center justify-between gap-4" },
      [
        React.createElement(
          "div",
          { key: "left", className: "flex items-center gap-3" },
          [
            React.createElement(
              "button",
              {
                key: "menu",
                type: "button",
                className: "inline-flex h-11 items-center rounded-full border border-slate-200 bg-white px-4 text-sm font-medium text-slate-700 shadow-sm lg:hidden",
                onClick: function onClick() {
                  setMobileOpen(mobileOpen === false);
                },
              },
              "Menu",
            ),
            React.createElement(
              "div",
              { key: "title" },
              [
                React.createElement("div", { key: "heading", className: "text-lg font-semibold text-slate-900" }, getPageTitle(location.pathname)),
                React.createElement("div", { key: "subheading", className: "text-sm text-slate-500" }, "Secure school fee operations workspace"),
              ],
            ),
          ],
        ),
        React.createElement(
          "div",
          { key: "right", className: "flex items-center gap-3" },
          [
            React.createElement(NotificationBell, { key: "bell", count: 0 }),
            React.createElement(UserMenu, { key: "user", fullName: fullName, roleLabel: roleLabel(role), showSettings: auth.hasAnyRole(["HEADTEACHER", "BURSAR"]), onLogout: auth.logout }),
          ],
        ),
      ],
    ),
  );

  const main = React.createElement(
    "main",
    { className: "flex-1 px-4 py-6 sm:px-6 lg:px-8" },
    React.createElement(Outlet),
  );

  return React.createElement(
    "div",
    { className: "min-h-screen bg-slate-100 text-slate-900" },
    [
      React.createElement(OfflineBanner, { key: "offline" }),
      overlay,
      React.createElement(
        "div",
        { key: "frame", className: "flex min-h-screen" },
        [
          sidebar,
          React.createElement(
            "div",
            { key: "content", className: "flex min-h-screen flex-1 flex-col lg:pl-0" },
            [header, main],
          ),
        ],
      ),
    ],
  );
}
