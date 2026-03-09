import type { DashboardResponse, DashboardType } from "@/types/dashboard";
import { handleAPIError } from "@/lib/errorHandler";

const BASE_URL = "/api/v1/reports/dashboard";

async function readResponse(response: Response) {
  const contentType = response.headers.get("content-type");
  if (contentType) {
    if (contentType.includes("application/json")) {
      return response.json();
    }
  }
  return response.text();
}

async function apiGet(url: string) {
  const token = localStorage.getItem("access_token");
  const headers: any = { "Content-Type": "application/json" };
  if (token) {
    headers.Authorization = "Bearer " + token;
  }
  const response = await fetch(url, { headers: headers, credentials: "include" });
  const payload = await readResponse(response);
  if (!response.ok) {
    handleAPIError(payload);
  }
  return payload as DashboardResponse;
}

export async function fetchDashboard(type: DashboardType) {
  return apiGet(BASE_URL + "/" + type + "/");
}
