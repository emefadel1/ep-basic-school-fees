import React from "react";
import { useAuth } from "@/context/AuthContext";
import PlaceholderPage from "@/pages/PlaceholderPage";
import BoardDashboardPage from "@/pages/dashboard/BoardDashboardPage";
import BursarDashboardPage from "@/pages/dashboard/BursarDashboardPage";
import ContactDashboardPage from "@/pages/dashboard/ContactDashboardPage";
import HeadteacherDashboardPage from "@/pages/dashboard/HeadteacherDashboardPage";
import TeacherDashboardPage from "@/pages/dashboard/TeacherDashboardPage";

export default function DashboardHomePage() {
  const auth = useAuth();

  if (auth.user === null) {
    return React.createElement(PlaceholderPage, {
      title: "Dashboard unavailable",
      description: "Sign in again to load your dashboard.",
      actions: [{ label: "Go to login", to: "/login" }],
    });
  }

  switch (auth.user.role) {
    case "CONTACT_PERSON":
      return React.createElement(ContactDashboardPage);
    case "HEADTEACHER":
      return React.createElement(HeadteacherDashboardPage);
    case "BURSAR":
      return React.createElement(BursarDashboardPage);
    case "BOARD":
      return React.createElement(BoardDashboardPage);
    default:
      return React.createElement(TeacherDashboardPage);
  }
}
