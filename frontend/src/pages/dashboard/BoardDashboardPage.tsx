import SummaryCard from "@/components/dashboard/SummaryCard";
import { useDashboardData } from "@/hooks/useDashboardData";

export default function BoardDashboardPage() {
  const { data, isPending, error } = useDashboardData("board");

  if (isPending) return <div className="p-6">Loading dashboard...</div>;
  if (error || !data || data.dashboard_type !== "board") {
    return <div className="p-6">Failed to load board dashboard.</div>;
  }

  return (
    <div className="space-y-6 p-6">
      <h1 className="text-2xl font-bold">Board Dashboard</h1>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
        <SummaryCard label="Total Students" value={data.board_summary.total_students} />
        <SummaryCard label="Total Collection" value={data.board_summary.total_collection} />
        <SummaryCard label="Monthly Collection" value={data.board_summary.monthly_collection} />
        <SummaryCard label="School Retention" value={data.board_summary.school_retention_total} />
      </div>

      <div className="rounded-2xl border bg-white p-4 shadow-sm">
        <h2 className="mb-4 text-lg font-semibold">Arrears Summary</h2>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          <SummaryCard label="Outstanding" value={data.arrears_summary.total_outstanding} />
          <SummaryCard label="Pending" value={data.arrears_summary.pending_count} />
          <SummaryCard label="Partial" value={data.arrears_summary.partial_count} />
        </div>
      </div>

      <div className="rounded-2xl border bg-white p-4 shadow-sm">
        <h2 className="mb-4 text-lg font-semibold">Top Staff Earnings</h2>
        <div className="space-y-2">
          {data.staff_earnings_summary.map((row, index) => (
            <div key={index} className="flex items-center justify-between rounded-lg border p-3">
              <span>{row.staff__username}</span>
              <span>{row.total}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}