import { useEffect, useState } from "react";
import { api } from "../api/client";
import AppLayout from "../components/AppLayout.jsx";
import { formatDate } from "../utils/formatters";

function AuditLogsPage() {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState("");
  const [filterAction, setFilterAction] = useState("all");
  const [page, setPage] = useState(1);
  const [pagination, setPagination] = useState({
    count: 0,
    page: 1,
    page_size: 10,
    total_pages: 1,
  });

  useEffect(() => {
    const fetchLogs = async () => {
      setLoading(true);
      setErrorMessage("");

      try {
        const response = await api.get("/audit/logs/", {
          params: {
            action: filterAction,
            page,
            page_size: 10,
          },
        });

        setLogs(response.data.results);
        setPagination({
          count: response.data.count,
          page: response.data.page,
          page_size: response.data.page_size,
          total_pages: response.data.total_pages,
        });
      } catch (error) {
        if (error.response?.data?.detail) {
          setErrorMessage(error.response.data.detail);
        } else if (error.response?.data?.error) {
          setErrorMessage(error.response.data.error);
        } else if (error.message) {
          setErrorMessage(error.message);
        } else {
          setErrorMessage("Could not load audit logs");
        }
      } finally {
        setLoading(false);
      }
    };

    fetchLogs();
  }, [filterAction, page]);

  const handleActionChange = (newAction) => {
    setFilterAction(newAction);
    setPage(1);
  };

  const getActionBadgeClass = (action) => {
    if (action === "PAYMENT_CREATED") return "badge-info";
    if (action === "PAYMENT_COMPLETED") return "badge-success";
    if (action === "WALLET_UPDATED") return "badge-info";
    return "badge-info";
  };

  return (
    <Layout
      title="Audit Logs"
      subtitle="Trazabilidad de eventos relevantes de tu cuenta."
    >
      <div className="card" style={{ marginBottom: "18px" }}>
        <div
          style={{
            display: "flex",
            gap: "0.75rem",
            flexWrap: "wrap",
            alignItems: "center",
          }}
        >
          <strong>Action:</strong>

          <button
            type="button"
            className={filterAction === "all" ? "btn btn-primary" : "btn btn-secondary"}
            onClick={() => handleActionChange("all")}
          >
            All
          </button>

          <button
            type="button"
            className={filterAction === "PAYMENT_CREATED" ? "btn btn-primary" : "btn btn-secondary"}
            onClick={() => handleActionChange("PAYMENT_CREATED")}
          >
            Payment Created
          </button>

          <button
            type="button"
            className={filterAction === "PAYMENT_COMPLETED" ? "btn btn-primary" : "btn btn-secondary"}
            onClick={() => handleActionChange("PAYMENT_COMPLETED")}
          >
            Payment Completed
          </button>

          <button
            type="button"
            className={filterAction === "WALLET_UPDATED" ? "btn btn-primary" : "btn btn-secondary"}
            onClick={() => handleActionChange("WALLET_UPDATED")}
          >
            Wallet Updated
          </button>
        </div>
      </div>

      {loading && <p>Loading audit logs...</p>}

      {errorMessage && (
        <div className="message message-error">{errorMessage}</div>
      )}

      {!loading && !errorMessage && logs.length === 0 && (
        <div className="card">
          <p>No audit logs found for the selected filter.</p>
        </div>
      )}

      {!loading && !errorMessage && logs.length > 0 && (
        <>
          <div className="card" style={{ marginBottom: "18px" }}>
            <p style={{ margin: 0 }}>
              Showing page <strong>{pagination.page}</strong> of{" "}
              <strong>{pagination.total_pages}</strong> — total logs:{" "}
              <strong>{pagination.count}</strong>
            </p>
          </div>

          <div className="card table-wrapper">
            <table className="table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Action</th>
                  <th>Entity Type</th>
                  <th>Entity ID</th>
                  <th>Metadata</th>
                  <th>Created At</th>
                </tr>
              </thead>

              <tbody>
                {logs.map((log) => (
                  <tr key={log.id}>
                    <td>{log.id}</td>

                    <td>
                      <span className={`badge ${getActionBadgeClass(log.action)}`}>
                        {log.action}
                      </span>
                    </td>

                    <td>{log.entity_type || "-"}</td>

                    <td>{log.entity_id ?? "-"}</td>

                    <td>
                      <pre
                        style={{
                          margin: 0,
                          whiteSpace: "pre-wrap",
                          wordBreak: "break-word",
                          fontSize: "0.85rem",
                        }}
                      >
                        {JSON.stringify(log.metadata || {}, null, 2)}
                      </pre>
                    </td>

                    <td>{formatDate(log.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div
            className="card"
            style={{
              marginTop: "18px",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              gap: "1rem",
              flexWrap: "wrap",
            }}
          >
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => setPage((prev) => prev - 1)}
              disabled={pagination.page <= 1}
            >
              Previous
            </button>

            <p style={{ margin: 0 }}>
              Page {pagination.page} of {pagination.total_pages}
            </p>

            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => setPage((prev) => prev + 1)}
              disabled={pagination.page >= pagination.total_pages}
            >
              Next
            </button>
          </div>
        </>
      )}
    </Layout>
  );
}

export default AuditLogsPage;