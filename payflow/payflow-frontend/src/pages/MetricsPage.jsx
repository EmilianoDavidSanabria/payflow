import { useEffect, useState } from "react";
import { api } from "../api/client";
import AppLayout from "../components/AppLayout.jsx";

function MetricsPage() {
  const [metrics, setMetrics] = useState(null);
  const [health, setHealth] = useState(null);
  const [loading, setLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState("");

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [metricsResponse, healthResponse] = await Promise.all([
          api.get("/core/metrics/"),
          api.get("/core/health/"),
        ]);

        setMetrics(metricsResponse.data);
        setHealth(healthResponse.data);
      } catch (error) {
        console.error("ERROR LOADING METRICS:", error);

        if (error.response?.data?.detail) {
          setErrorMessage(error.response.data.detail);
        } else if (error.message) {
          setErrorMessage(error.message);
        } else {
          setErrorMessage("Could not load metrics");
        }
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  return (
    <Layout
      title="Metrics"
      subtitle="Estado técnico general del sistema."
    >
      {loading && <p>Loading metrics...</p>}
      {errorMessage && <div className="message message-error">{errorMessage}</div>}

      {!loading && !errorMessage && health && (
        <div className="card">
          <h2>Health</h2>
          <p>
            <strong>Status:</strong>{" "}
            <span className="badge badge-success">{health.status}</span>
          </p>
          <p><strong>Message:</strong> {health.message}</p>
        </div>
      )}

      {!loading && !errorMessage && metrics && (
        <div className="grid grid-2">
          <div className="card stat-card">
            <h3>Total Users</h3>
            <p className="stat-value">{metrics.total_users}</p>
          </div>

          <div className="card stat-card">
            <h3>Total Wallets</h3>
            <p className="stat-value">{metrics.total_wallets}</p>
          </div>

          <div className="card stat-card">
            <h3>Total Payments</h3>
            <p className="stat-value">{metrics.total_payments}</p>
          </div>

          <div className="card stat-card">
            <h3>Total Ledger Entries</h3>
            <p className="stat-value">{metrics.total_ledger_entries}</p>
          </div>

          <div className="card stat-card">
            <h3>Total Audit Logs</h3>
            <p className="stat-value">{metrics.total_audit_logs}</p>
          </div>
        </div>
      )}
    </Layout>
  );
}

export default MetricsPage;