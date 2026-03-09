import React from "react";
import { BrowserRouter, Navigate, useRoutes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import ErrorBoundary from "@/components/ErrorBoundary";
import { ProtectedRoute, PublicOnlyRoute } from "@/components/auth/ProtectedRoute";
import DashboardLayout from "@/components/layout/DashboardLayout";
import { ToastProvider } from "@/components/ui/ToastProvider";
import { AuthProvider } from "@/context/AuthContext";
import DashboardHomePage from "@/pages/DashboardHomePage";
import LoginPage from "@/pages/LoginPage";
import PlaceholderPage from "@/pages/PlaceholderPage";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

function AppRoutes() {
  return useRoutes([
    {
      path: "/login",
      element: React.createElement(PublicOnlyRoute, null, React.createElement(LoginPage)),
    },
    {
      path: "/",
      element: React.createElement(ProtectedRoute),
      children: [
        {
          element: React.createElement(DashboardLayout),
          children: [
            { index: true, element: React.createElement(Navigate, { to: "/dashboard", replace: true }) },
            { path: "dashboard", element: React.createElement(DashboardHomePage) },
            {
              path: "fees",
              element: React.createElement(ProtectedRoute, { allowedRoles: ["TEACHER", "CONTACT_PERSON", "HEADTEACHER", "BURSAR"] }),
              children: [
                { index: true, element: React.createElement(PlaceholderPage, { title: "Fee collection", description: "Collections, arrears, waivers, and payment actions will land here.", actions: [{ label: "Open dashboard", to: "/dashboard" }] }) },
              ],
            },
            {
              path: "sessions",
              element: React.createElement(ProtectedRoute, { allowedRoles: ["HEADTEACHER", "BURSAR"] }),
              children: [
                { index: true, element: React.createElement(PlaceholderPage, { title: "Sessions", description: "Open, approve, reject, unlock, and distribution workflows connect through this area.", actions: [{ label: "View dashboard", to: "/dashboard" }] }) },
              ],
            },
            {
              path: "reports",
              element: React.createElement(ProtectedRoute, { allowedRoles: ["CONTACT_PERSON", "HEADTEACHER", "BURSAR", "BOARD"] }),
              children: [
                { index: true, element: React.createElement(PlaceholderPage, { title: "Reports", description: "Reporting routes are scaffolded here so dashboards and exports have a shared home.", actions: [{ label: "Back to dashboard", to: "/dashboard" }] }) },
              ],
            },
            {
              path: "students",
              element: React.createElement(ProtectedRoute, { allowedRoles: ["TEACHER", "CONTACT_PERSON", "HEADTEACHER", "BURSAR"] }),
              children: [
                { index: true, element: React.createElement(PlaceholderPage, { title: "Students", description: "Student records, balances, and class fee context will appear in this section.", actions: [{ label: "Back to dashboard", to: "/dashboard" }] }) },
              ],
            },
            {
              path: "staff",
              element: React.createElement(ProtectedRoute, { allowedRoles: ["HEADTEACHER", "BURSAR", "BOARD"] }),
              children: [
                { index: true, element: React.createElement(PlaceholderPage, { title: "Staff", description: "Staff management and earnings views will be anchored here.", actions: [{ label: "Back to dashboard", to: "/dashboard" }] }) },
              ],
            },
            {
              path: "audit",
              element: React.createElement(ProtectedRoute, { allowedRoles: ["BURSAR"] }),
              children: [
                { index: true, element: React.createElement(PlaceholderPage, { title: "Audit and compliance", description: "Audit browsing is routed here and can now expand against the new backend audit endpoints.", actions: [{ label: "Back to dashboard", to: "/dashboard" }] }) },
              ],
            },
            {
              path: "settings",
              element: React.createElement(ProtectedRoute, { allowedRoles: ["HEADTEACHER", "BURSAR"] }),
              children: [
                { index: true, element: React.createElement(PlaceholderPage, { title: "Settings", description: "System settings, notifications, and profile management belong in this shell area.", actions: [{ label: "Back to dashboard", to: "/dashboard" }] }) },
              ],
            },
          ],
        },
      ],
    },
    { path: "*", element: React.createElement(PlaceholderPage, { title: "Page not found", description: "This route is not wired yet. Use the dashboard to continue.", actions: [{ label: "Go to dashboard", to: "/dashboard" }] }) },
  ]);
}

export default function App() {
  return React.createElement(
    ErrorBoundary,
    null,
    React.createElement(
      QueryClientProvider,
      { client: queryClient },
      React.createElement(
        AuthProvider,
        null,
        React.createElement(
          ToastProvider,
          null,
          React.createElement(
            BrowserRouter,
            null,
            React.createElement(
              React.Suspense,
              { fallback: React.createElement("div", { className: "flex min-h-screen items-center justify-center bg-slate-100 text-sm text-slate-600" }, "Loading workspace...") },
              React.createElement(AppRoutes),
            ),
          ),
        ),
      ),
    ),
  );
}
