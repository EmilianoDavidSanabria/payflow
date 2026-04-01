import { useEffect, useMemo, useState } from "react";
import { api } from "../api/client";
import Layout from "../components/Layout.jsx";
import { formatCurrency, formatDate } from "../utils/formatters";
import { Link } from "react-router-dom";

function PaymentHistoryPage() {
  const [payments, setPayments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState("");
  const [filterType, setFilterType] = useState("all");
  const [filterStatus, setFilterStatus] = useState("all");
  const [page, setPage] = useState(1);
  const [pagination, setPagination] = useState({
    count: 0,
    page: 1,
    page_size: 10,
    total_pages: 1,
  });

  useEffect(() => {
    const fetchPayments = async () => {
      setLoading(true);
      setErrorMessage("");

      try {
        const response = await api.get("/payments/history/", {
          params: {
            type: filterType,
            status: filterStatus,
            page,
            page_size: 10,
          },
        });

        setPayments(response.data.results);
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
          setErrorMessage("Could not load payment history.");
        }
      } finally {
        setLoading(false);
      }
    };

    fetchPayments();
  }, [filterType, filterStatus, page]);

  const handleTypeChange = (newType) => {
    setFilterType(newType);
    setPage(1);
  };

  const handleStatusChange = (newStatus) => {
    setFilterStatus(newStatus);
    setPage(1);
  };

  const getStatusBadgeClass = (status) => {
    if (status === "COMPLETED") return "badge-success";
    if (status === "PENDING") return "badge-info";
    if (status === "FAILED") return "badge-error";
    return "badge-info";
  };

  const getDirectionBadgeClass = (direction) => {
    if (direction === "received") return "badge-success";
    if (direction === "sent") return "badge-info";
    return "badge-info";
  };

  const getDirectionLabel = (direction) => {
    if (direction === "received") return "Received";
    if (direction === "sent") return "Sent";
    return "Transfer";
  };

  const summary = useMemo(() => {
    const result = {
      sent: 0,
      received: 0,
      completed: 0,
    };

    for (const payment of payments) {
      if (payment.direction === "sent") result.sent += 1;
      if (payment.direction === "received") result.received += 1;
      if (payment.status === "COMPLETED") result.completed += 1;
    }

    return result;
  }, [payments]);

  return (
    <Layout
      title="Payment History"
      subtitle="Review sent and received payments with filtering and detail views."
    >
      <div className="grid grid-3" style={{ marginBottom: "18px" }}>
        <div className="card">
          <h3 style={{ marginTop: 0 }}>Results on current page</h3>
          <p className="stat-value" style={{ fontSize: "1.7rem" }}>
            {payments.length}
          </p>
          <p style={{ margin: 0, opacity: 0.8 }}>
            Payments currently visible in the table.
          </p>
        </div>

        <div className="card">
          <h3 style={{ marginTop: 0 }}>Sent on current page</h3>
          <p className="stat-value" style={{ fontSize: "1.7rem" }}>
            {summary.sent}
          </p>
          <p style={{ margin: 0, opacity: 0.8 }}>
            Payments where you acted as sender.
          </p>
        </div>

        <div className="card">
          <h3 style={{ marginTop: 0 }}>Completed on current page</h3>
          <p className="stat-value" style={{ fontSize: "1.7rem" }}>
            {summary.completed}
          </p>
          <p style={{ margin: 0, opacity: 0.8 }}>
            Payments already settled successfully.
          </p>
        </div>
      </div>

      <div className="card" style={{ marginBottom: "18px" }}>
        <p className="eyebrow">Filters</p>
        <h2 style={{ marginBottom: "12px" }}>History controls</h2>

        <div
          style={{
            display: "flex",
            gap: "0.75rem",
            flexWrap: "wrap",
            alignItems: "center",
            marginBottom: "12px",
          }}
        >
          <strong>Type:</strong>

          <button
            type="button"
            className={filterType === "all" ? "btn btn-primary" : "btn btn-secondary"}
            onClick={() => handleTypeChange("all")}
          >
            All
          </button>

          <button
            type="button"
            className={filterType === "sent" ? "btn btn-primary" : "btn btn-secondary"}
            onClick={() => handleTypeChange("sent")}
          >
            Sent
          </button>

          <button
            type="button"
            className={filterType === "received" ? "btn btn-primary" : "btn btn-secondary"}
            onClick={() => handleTypeChange("received")}
          >
            Received
          </button>
        </div>

        <div
          style={{
            display: "flex",
            gap: "0.75rem",
            flexWrap: "wrap",
            alignItems: "center",
          }}
        >
          <strong>Status:</strong>

          <button
            type="button"
            className={filterStatus === "all" ? "btn btn-primary" : "btn btn-secondary"}
            onClick={() => handleStatusChange("all")}
          >
            All
          </button>

          <button
            type="button"
            className={filterStatus === "COMPLETED" ? "btn btn-primary" : "btn btn-secondary"}
            onClick={() => handleStatusChange("COMPLETED")}
          >
            Completed
          </button>

          <button
            type="button"
            className={filterStatus === "PENDING" ? "btn btn-primary" : "btn btn-secondary"}
            onClick={() => handleStatusChange("PENDING")}
          >
            Pending
          </button>

          <button
            type="button"
            className={filterStatus === "FAILED" ? "btn btn-primary" : "btn btn-secondary"}
            onClick={() => handleStatusChange("FAILED")}
          >
            Failed
          </button>
        </div>
      </div>

      {loading && <p>Loading payments...</p>}

      {errorMessage && (
        <div className="message message-error">{errorMessage}</div>
      )}

      {!loading && !errorMessage && payments.length === 0 && (
        <div className="card">
          <p style={{ marginBottom: "8px" }}>
            No payments found for the selected filters.
          </p>
          <p style={{ margin: 0, opacity: 0.8 }}>
            Try adjusting the filters or create a new payment from the Payments page.
          </p>
        </div>
      )}

      {!loading && !errorMessage && payments.length > 0 && (
        <>
          <div className="card" style={{ marginBottom: "18px" }}>
            <p style={{ margin: 0 }}>
              Showing page <strong>{pagination.page}</strong> of{" "}
              <strong>{pagination.total_pages}</strong> — total payments:{" "}
              <strong>{pagination.count}</strong>
            </p>
          </div>

          <div className="card table-wrapper">
            <table className="table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Type</th>
                  <th>Counterparty</th>
                  <th>Amount</th>
                  <th>Status</th>
                  <th>Created at</th>
                </tr>
              </thead>

              <tbody>
                {payments.map((payment) => (
                  <tr key={payment.id}>
                    <td>
                      <Link to={`/payments/${payment.id}`}>{payment.id}</Link>
                    </td>

                    <td>
                      <span className={`badge ${getDirectionBadgeClass(payment.direction)}`}>
                        {getDirectionLabel(payment.direction)}
                      </span>
                    </td>

                    <td>
                      {payment.direction === "sent"
                        ? `To @${payment.counterparty_username}`
                        : `From @${payment.counterparty_username}`}
                    </td>

                    <td>{formatCurrency(payment.amount)}</td>

                    <td>
                      <span className={`badge ${getStatusBadgeClass(payment.status)}`}>
                        {payment.status}
                      </span>
                    </td>

                    <td>{formatDate(payment.created_at)}</td>
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

export default PaymentHistoryPage;