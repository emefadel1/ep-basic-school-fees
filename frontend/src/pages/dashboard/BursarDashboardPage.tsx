import SummaryCard from "@/components/dashboard/SummaryCard";
import { useDashboardData } from "@/hooks/useDashboardData";

export default function BursarDashboardPage() {
  const { data, isPending, error } = useDashboardData("bursar");

  if (isPending) return <div className="p-6">Loading dashboard...</div>;
  if (error || !data || data.dashboard_type !== "bursar") {
    return <div className="p-6">Failed to load bursar dashboard.</div>;
  }

  return (
    <div className="space-y-6 p-6">
      <h1 className="text-2xl font-bold">Bursar Dashboard</h1>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
        <SummaryCard label="Total Collection" value={data.admin_summary.total_collection} />
        <SummaryCard label="School Retention" value={data.admin_summary.school_retention} />
        <SummaryCard label="Admin Fees" value={data.admin_summary.admin_fees} />
        <SummaryCard label="Staff Distribution" value={data.admin_summary.staff_distribution} />
      </div>

      <div className="rounded-2xl border bg-white p-4 shadow-sm">
        <h2 className="mb-4 text-lg font-semibold">Pending Approvals</h2>
        <div className="space-y-2">
          {data.pending_approvals.map((row) => (
            <div key={row.id} className="flex items-center justify-between rounded-lg border p-3">
              <span>{row.date}</span>
              <span>{row.status}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}