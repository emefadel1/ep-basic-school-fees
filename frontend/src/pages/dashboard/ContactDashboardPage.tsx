import SummaryCard from "@/components/dashboard/SummaryCard";
import { useDashboardData } from "@/hooks/useDashboardData";

export default function ContactDashboardPage() {
  const { data, isPending, error } = useDashboardData("contact");

  if (isPending) return <div className="p-6">Loading dashboard...</div>;
  if (error || !data || data.dashboard_type !== "contact") {
    return <div className="p-6">Failed to load contact dashboard.</div>;
  }

  return (
    <div className="space-y-6 p-6">
      <h1 className="text-2xl font-bold">Contact Person Dashboard</h1>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
        <SummaryCard label="Category" value={data.category_overview.category_name} />
        <SummaryCard label="Classes" value={data.category_overview.total_classes} />
        <SummaryCard label="Students" value={data.category_overview.total_students} />
        <SummaryCard label="Rate" value={`${data.category_overview.collection_rate.toFixed(1)}%`} />
      </div>

      <div className="rounded-2xl border bg-white p-4 shadow-sm">
        <h2 className="mb-4 text-lg font-semibold">Classes Summary</h2>
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="border-b text-left">
                <th className="p-2">Class</th>
                <th className="p-2">Teacher</th>
                <th className="p-2">Students</th>
                <th className="p-2">Expected</th>
                <th className="p-2">Collected</th>
                <th className="p-2">Rate</th>
              </tr>
            </thead>
            <tbody>
              {data.classes_summary_table.map((row) => (
                <tr key={row.class_id} className="border-b">
                  <td className="p-2">{row.class_code}</td>
                  <td className="p-2">{row.teacher_name}</td>
                  <td className="p-2">{row.students_count}</td>
                  <td className="p-2">{row.expected}</td>
                  <td className="p-2">{row.collected}</td>
                  <td className="p-2">{row.rate.toFixed(1)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}