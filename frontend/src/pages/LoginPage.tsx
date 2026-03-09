import React from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { getErrorMessage, getFieldErrors } from "@/lib/errorHandler";
import { useToast } from "@/components/ui/ToastProvider";

export default function LoginPage() {
  const auth = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const toast = useToast();
  const [username, setUsername] = React.useState("");
  const [password, setPassword] = React.useState("");
  const [fieldErrors, setFieldErrors] = React.useState({} as any);
  const [submitError, setSubmitError] = React.useState("");

  let redirectTo = "/dashboard";
  const routeState: any = location.state;
  if (routeState !== null) {
    if (typeof routeState === "object") {
      if (typeof routeState.from === "string") {
        redirectTo = routeState.from;
      }
    }
  }

  async function onSubmit(event: any) {
    event.preventDefault();
    setFieldErrors({});
    setSubmitError("");
    try {
      await auth.login({ username: username, password: password });
      toast.pushToast({ title: "Signed in", description: "Welcome back.", tone: "success" });
      navigate(redirectTo, { replace: true });
    } catch (error) {
      const nextFieldErrors = getFieldErrors(error);
      setFieldErrors(nextFieldErrors);
      const message = getErrorMessage(error);
      setSubmitError(message);
      if (Object.keys(nextFieldErrors).length === 0) {
        toast.pushToast({ title: "Sign in failed", description: message, tone: "error" });
      }
    }
  }

  const cardChildren = [
    React.createElement(
      "div",
      { key: "intro" },
      [
        React.createElement("div", { key: "eyebrow", className: "text-xs font-semibold uppercase tracking-[0.3em] text-slate-500" }, "E.P Basic School"),
        React.createElement("h1", { key: "title", className: "mt-3 text-3xl font-semibold text-slate-900" }, "Sign in"),
        React.createElement("p", { key: "description", className: "mt-2 text-sm text-slate-600" }, "Use your school account to open the fee distribution workspace."),
      ],
    ),
  ];

  if (submitError !== "") {
    cardChildren.push(
      React.createElement(
        "div",
        { key: "error", className: "rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800" },
        submitError,
      ),
    );
  }

  cardChildren.push(
    React.createElement(
      "form",
      { key: "form", className: "space-y-5", onSubmit: onSubmit },
      [
        React.createElement(
          "div",
          { key: "username" },
          [
            React.createElement("label", { key: "label", htmlFor: "username", className: "mb-2 block text-sm font-medium text-slate-700" }, "Username"),
            React.createElement("input", { id: "username", key: "input", className: "w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 shadow-sm", value: username, onChange: function onChange(event: any) { setUsername(event.target.value); }, autoComplete: "username" }),
            fieldErrors.username !== undefined ? React.createElement("div", { key: "error", className: "mt-2 text-sm text-rose-700" }, fieldErrors.username) : null,
          ],
        ),
        React.createElement(
          "div",
          { key: "password" },
          [
            React.createElement("label", { key: "label", htmlFor: "password", className: "mb-2 block text-sm font-medium text-slate-700" }, "Password"),
            React.createElement("input", { id: "password", key: "input", type: "password", className: "w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 shadow-sm", value: password, onChange: function onChange(event: any) { setPassword(event.target.value); }, autoComplete: "current-password" }),
            fieldErrors.password !== undefined ? React.createElement("div", { key: "error", className: "mt-2 text-sm text-rose-700" }, fieldErrors.password) : null,
          ],
        ),
        React.createElement(
          "button",
          {
            key: "submit",
            type: "submit",
            className: "w-full rounded-full bg-slate-900 px-5 py-3 text-sm font-semibold text-white shadow-lg shadow-slate-300",
            disabled: auth.isLoading === true,
          },
          auth.isLoading === true ? "Signing in..." : "Sign in",
        ),
      ],
    ),
  );

  return React.createElement(
    "div",
    { className: "flex min-h-screen items-center justify-center bg-slate-100 px-4 py-12" },
    React.createElement(
      "div",
      { className: "w-full max-w-md rounded-[2rem] border border-slate-200 bg-white p-8 shadow-2xl shadow-slate-200" },
      cardChildren,
    ),
  );
}
