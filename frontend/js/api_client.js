const API_BASE_URL = "http://localhost:8000";

export async function fetchDashboardSnapshot() {
  const response = await fetch(`${API_BASE_URL}/api/dashboard`);

  if (!response.ok) {
    throw new Error(`Dashboard request failed with status ${response.status}`);
  }

  return response.json();
}
