import React from "react";
import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import PlaceholderPage from "@/pages/PlaceholderPage";

function LoadingScreen() {
  return React.createElement(
    "div",
    { className: "flex min-h-screen items-center justify-center bg-slate-100 px-6 text-sm text-slate-600" },
    "Loading application...",
  );
}

export function ProtectedRoute(props: any) {
  const auth = useAuth();
  const location = useLocation();

  if (auth.isLoading === true) {
    return React.createElement(LoadingScreen);
  }

  if (auth.isAuthenticated !== true) {
    return React.createElement(Navigate, {
      to: "/login",
      replace: true,
      state: { from: location.pathname },
    });
  }

  if (props.allowedRoles !== undefined) {
    if (auth.hasAnyRole(props.allowedRoles) === false) {
      return React.createElement(PlaceholderPage, {
        title: "Access denied",
        description: "Your account does not have permission to open this area.",
        actions: [{ label: "Back to dashboard", to: "/dashboard" }],
      });
    }
  }

  if (props.children !== undefined) {
    return React.createElement(React.Fragment, null, props.children);
  }

  return React.createElement(Outlet);
}

export function PublicOnlyRoute(props: any) {
  const auth = useAuth();

  if (auth.isLoading === true) {
    return React.createElement(LoadingScreen);
  }

  if (auth.isAuthenticated === true) {
    return React.createElement(Navigate, { to: "/dashboard", replace: true });
  }

  if (props.children !== undefined) {
    return React.createElement(React.Fragment, null, props.children);
  }

  return React.createElement(Outlet);
}

export default ProtectedRoute;
