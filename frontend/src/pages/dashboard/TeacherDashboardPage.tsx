import React from "react";
import { Link } from "react-router-dom";
import SummaryCard from "@/components/dashboard/SummaryCard";
import { useDashboardData } from "@/hooks/useDashboardData";

function TeacherQuickActions(props: any) {
  const actions: any[] = [];
  if (props.quickActions.can_record_fees === true) {
    actions.push({ label: "Record fees", to: "/fees" });
  }
  if (props.quickActions.can_view_students === true) {
    actions.push({ label: "View students", to: "/students" });
  }
  if (props.quickActions.can_view_summary === true) {
    actions.push({ label: "Session summary", to: "/sessions" });
  }

  if (actions.length === 0) {
    return null;
  }

  return React.createElement(
    "div",
    { className: "rounded-2xl border bg-white p-4 shadow-sm" },
    [
      React.createElement("h2", { key: "title", className: "text-lg font-semibold" }, "Quick actions"),
      React.createElement(
        "div",
        { key: "actions", className: "mt-4 flex flex-wrap gap-3" },
        actions.map(function renderAction(action: any, index: number) {
          return React.createElement(
            Link,
            {
              key: String(index),
              to: action.to,
              className: "rounded-full bg-slate-900 px-4 py-2 text-sm font-medium text-white shadow-sm",
            },
            action.label,
          );
        }),
      ),
    ],
  );
}

export default function TeacherDashboardPage() {
  const query = useDashboardData("teacher");
  const data = query.data;

  if (query.isPending === true) {
    return React.createElement("div", { className: "p-6" }, "Loading dashboard...");
  }

  if (query.error) {
    return React.createElement("div", { className: "p-6" }, "Failed to load teacher dashboard.");
  }
  if (data === undefined) {
    return React.createElement("div", { className: "p-6" }, "Failed to load teacher dashboard.");
  }
  if (data === null) {
    return React.createElement("div", { className: "p-6" }, "Failed to load teacher dashboard.");
  }
  if (data.dashboard_type !== "teacher") {
    return React.createElement("div", { className: "p-6" }, "Failed to load teacher dashboard.");
  }

  return React.createElement(
    "div",
    { className: "space-y-6 p-6" },
    [
      React.createElement("h1", { key: "title", className: "text-2xl font-bold" }, "Teacher Dashboard"),
      React.createElement(TeacherQuickActions, { key: "quick-actions", quickActions: data.quick_actions }),
      React.createElement(
        "div",
        { key: "summary", className: "grid grid-cols-1 gap-4 md:grid-cols-4" },
        [
          React.createElement(SummaryCard, { key: "status", label: "Session Status", value: data.summary.session_status }),
          React.createElement(SummaryCard, { key: "submission", label: "Submission Status", value: data.summary.submission_status }),
          React.createElement(SummaryCard, { key: "progress", label: "Progress", value: data.summary.collection_progress }),
          React.createElement(SummaryCard, { key: "rate", label: "Rate", value: data.summary.collection_rate.toFixed(1) + "%" }),
        ],
      ),
      React.createElement(
        "div",
        { key: "earnings", className: "grid grid-cols-1 gap-4 md:grid-cols-4" },
        [
          React.createElement(SummaryCard, { key: "today", label: "Today Share", value: data.my_earnings.today_share }),
          React.createElement(SummaryCard, { key: "week", label: "Week Total", value: data.my_earnings.week_total }),
          React.createElement(SummaryCard, { key: "month", label: "Month Total", value: data.my_earnings.month_total }),
          React.createElement(SummaryCard, { key: "pending", label: "Pending Payment", value: data.my_earnings.pending_payment }),
        ],
      ),
      React.createElement(
        "div",
        { key: "table-card", className: "rounded-2xl border bg-white p-4 shadow-sm" },
        [
          React.createElement("h2", { key: "heading", className: "mb-4 text-lg font-semibold" }, "Class Collection Table"),
          React.createElement(
            "div",
            { key: "table-wrap", className: "overflow-x-auto" },
            React.createElement(
              "table",
              { className: "min-w-full text-sm" },
              [
                React.createElement(
                  "thead",
                  { key: "head" },
                  React.createElement(
                    "tr",
                    { className: "border-b text-left" },
                    [
                      React.createElement("th", { key: "student", className: "p-2" }, "Student"),
                      React.createElement("th", { key: "pool", className: "p-2" }, "Pool"),
                      React.createElement("th", { key: "expected", className: "p-2" }, "Expected"),
                      React.createElement("th", { key: "paid", className: "p-2" }, "Paid"),
                      React.createElement("th", { key: "status", className: "p-2" }, "Status"),
                    ],
                  ),
                ),
                React.createElement(
                  "tbody",
                  { key: "body" },
                  data.class_collection_table.map(function renderRow(row: any) {
                    return React.createElement(
                      "tr",
                      { key: row.id, className: "border-b" },
                      [
                        React.createElement("td", { key: "student", className: "p-2" }, row.student_name),
                        React.createElement("td", { key: "pool", className: "p-2" }, row.pool_type),
                        React.createElement("td", { key: "expected", className: "p-2" }, row.expected_fee),
                        React.createElement("td", { key: "paid", className: "p-2" }, row.amount_paid),
                        React.createElement("td", { key: "status", className: "p-2" }, row.status),
                      ],
                    );
                  }),
                ),
              ],
            ),
          ),
        ],
      ),
    ],
  );
}
