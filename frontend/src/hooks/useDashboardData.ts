import { useQuery } from "@tanstack/react-query";
import { fetchDashboard } from "@/services/dashboardApi";
import type { DashboardResponse, DashboardType } from "@/types/dashboard";

// TanStack Query supports polling with refetchInterval and freshness control with staleTime.
// Latest docs also use placeholderData/keepPreviousData for retaining prior results while refetching.
// See official docs: useQuery + paginated/lagged queries. :contentReference[oaicite:1]{index=1}

export function useDashboardData(type: DashboardType) {
  return useQuery<DashboardResponse>({
    queryKey: ["dashboard", type],
    queryFn: () => fetchDashboard(type),
    refetchInterval: 30000,
    refetchIntervalInBackground: false,
    staleTime: 15000,
    placeholderData: (previousData) => previousData,
  });
}