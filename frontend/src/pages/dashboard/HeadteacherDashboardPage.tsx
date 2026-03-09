import SummaryCard from "@/components/dashboard/SummaryCard";
import { useDashboardData } from "@/hooks/useDashboardData";

export default function HeadteacherDashboardPage() {
  const { data, isPending, error } = useDashboardData("headteacher");

  if (isPending) return <div className="p-6">Loading dashboard...</div>;
  if (error || !data || data.dashboard_type !== "headteacher") {
    return <div className="p-6">Failed to load headteacher dashboard.</div>;
  }

  return (
    <div className="space-y-6 p-6">
      <h1 className="text-2xl font-bold">Headteacher Dashboard</h1>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
        <SummaryCard label="Students" value={data.school_wide_summary.total_students} />
        <SummaryCard label="Teachers" value={data.school_wide_summary.total_teachers} />
        <SummaryCard label="Today Collection" value={data.school_wide_summary.today_collection} />
        <SummaryCard label="Rate" value={`${data.school_wide_summary.collection_rate.toFixed(1)}%`} />
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
        <SummaryCard label="Present" value={data.staff_attendance_overview.present_count} />
        <SummaryCard label="Late" value={data.staff_attendance_overview.late_count} />
        <SummaryCard label="Absent" value={data.staff_attendance_overview.absent_count} />
        <SummaryCard label="On Leave" value={data.staff_attendance_overview.on_leave_count} />
      </div>
    </div>
  );
}