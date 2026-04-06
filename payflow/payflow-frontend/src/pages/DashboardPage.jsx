import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api/client";
import AppLayout from "../components/AppLayout.jsx";
import {
  formatCurrency,
  formatDate,
  formatRelativeAmount,
} from "../utils/formatters";

function DashboardPage() {
  const [wallet, setWallet] = useState(null);
  const [recentSummary, setRecentSummary] = useState(null);
  const [recentPayments, setRecentPayments] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const navigate = useNavigate();

  useEffect(() => {
    async function fetchDashboardData() {
      try {
        setLoading(true);
        setError("");

        const response = await api.get("/core/dashboard-summary/");

        setWallet(response.data.wallet);
        setRecentSummary(response.data.recent_summary);
        setRecentPayments(response.data.recent_activity);
      } catch (error) {
        console.error("DASHBOARD ERROR:", error);
        setError("Could not load dashboard.");
      } finally {
        setLoading(false);
      }
    }

    fetchDashboardData();
  }, []);

  const getStatusBadgeClass = (status) => {
    if (status === "COMPLETED") return "badge-success";
    if (status === "PENDING") return "badge-info";
    if (status === "FAILED") return "badge-error";
    return "badge-info";
  };

  const activitySummary = useMemo(() => {
    const summary = {
      sent: 0,
      received: 0,
      pending: 0,
    };

    for (const payment of recentPayments) {
      if (payment.direction === "sent") summary.sent += 1;
      if (payment.direction === "received") summary.received += 1;
      if (payment.status === "PENDING") summary.pending += 1;
    }

    return summary;
  }, [recentPayments]);

  return (
    <AppLayout
      title="Dashboard"
      subtitle="Review your balance, recent payment activity, and the main flows available in PayFlow."
    >
      {error && <div className="message message-error">{error}</div>}

      {loading && !error && <p>Loading dashboard...</p>}

      {!loading && wallet && (
        <>
          <div className="grid grid-3" style={{ marginBottom: "18px" }}>
            <div className="card stat-card">
              <h3>Available balance</h3>
              <p className="stat-value">
                {formatCurrency(wallet.balance, wallet.currency)}
              </p>
              <p style={{ marginTop: "8px", opacity: 0.8 }}>
                Current wallet balance ready to use in PayFlow.
              </p>
            </div>

            <div className="card stat-card">
              <h3>Wallet currency</h3>
              <p className="stat-value">{wallet.currency}</p>
              <p style={{ marginTop: "8px", opacity: 0.8 }}>
                Default currency associated with your wallet.
              </p>
            </div>

            <div className="card stat-card">
              <h3>Recent activity</h3>
              <p className="stat-value" style={{ fontSize: "1.5rem" }}>
                {recentPayments.length}
              </p>
              <p style={{ marginTop: "8px", opacity: 0.8 }}>
                Latest payments surfaced in your dashboard view.
              </p>
            </div>
          </div>

          {recentSummary && (
            <div className="grid grid-2" style={{ marginBottom: "18px" }}>
              <div className="card stat-card">
                <p className="eyebrow">Outgoing activity</p>
                <h3>Sent in the last {recentSummary.period_days} days</h3>
                <p className="stat-value">
                  {formatCurrency(recentSummary.sent_total, wallet.currency)}
                </p>
                <p style={{ marginTop: "8px", opacity: 0.8 }}>
                  {recentSummary.sent_count} completed payment
                  {recentSummary.sent_count === 1 ? "" : "s"} sent to other users.
                </p>
              </div>

              <div className="card stat-card">
                <p className="eyebrow">Incoming activity</p>
                <h3>Received in the last {recentSummary.period_days} days</h3>
                <p className="stat-value">
                  {formatCurrency(recentSummary.received_total, wallet.currency)}
                </p>
                <p style={{ marginTop: "8px", opacity: 0.8 }}>
                  {recentSummary.received_count} completed payment
                  {recentSummary.received_count === 1 ? "" : "s"} received into your wallet.
                </p>
              </div>
            </div>
          )}

          <div className="card" style={{ marginBottom: "18px" }}>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "flex-start",
                gap: "16px",
                flexWrap: "wrap",
              }}
            >
              <div>
                <p className="eyebrow">Quick access</p>
                <h2 style={{ marginBottom: "8px" }}>Core product areas</h2>
                <p style={{ margin: 0, opacity: 0.8, maxWidth: "700px" }}>
                  Move money, review wallet funding, inspect payment history, and
                  explore traceability and operational metrics from one place.
                </p>
              </div>

              <Link to="/payments" className="btn btn-primary">
                New payment
              </Link>
            </div>

            <div className="grid grid-3" style={{ marginTop: "18px" }}>
              <Link to="/wallet" className="card">
                <h2>Wallet</h2>
                <p>
                  Check balance, start top-ups through Mercado Pago, and review
                  funding transactions.
                </p>
              </Link>

              <Link to="/payments" className="card">
                <h2>Payments</h2>
                <p>
                  Send money, request payments, and manage pending payment requests.
                </p>
              </Link>

              <Link to="/payments/history" className="card">
                <h2>Payment History</h2>
                <p>
                  Review sent and received payments with filters, dates, and detail views.
                </p>
              </Link>

              <Link to="/audit-logs" className="card">
                <h2>Audit Logs</h2>
                <p>
                  Explore traceability, operational events, and audit metadata.
                </p>
              </Link>

              <Link to="/metrics" className="card">
                <h2>Metrics</h2>
                <p>
                  Inspect health and business-oriented technical metrics exposed by the backend.
                </p>
              </Link>

              <Link to="/wallet" className="card">
                <h2>Funding Flow</h2>
                <p>
                  Follow pending, completed, and failed wallet funding operations in one place.
                </p>
              </Link>
            </div>
          </div>

          <div className="grid grid-3" style={{ marginBottom: "18px" }}>
            <div className="card">
              <h3 style={{ marginTop: 0 }}>Sent in current activity</h3>
              <p className="stat-value" style={{ fontSize: "1.7rem" }}>
                {activitySummary.sent}
              </p>
              <p style={{ margin: 0, opacity: 0.8 }}>
                Payments where you acted as sender in the current dashboard slice.
              </p>
            </div>

            <div className="card">
              <h3 style={{ marginTop: 0 }}>Received in current activity</h3>
              <p className="stat-value" style={{ fontSize: "1.7rem" }}>
                {activitySummary.received}
              </p>
              <p style={{ margin: 0, opacity: 0.8 }}>
                Payments where funds came into your wallet in this recent view.
              </p>
            </div>

            <div className="card">
              <h3 style={{ marginTop: 0 }}>Pending in current activity</h3>
              <p className="stat-value" style={{ fontSize: "1.7rem" }}>
                {activitySummary.pending}
              </p>
              <p style={{ margin: 0, opacity: 0.8 }}>
                Payments not yet in a terminal state in the recent activity slice.
              </p>
            </div>
          </div>

          <div className="card">
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                gap: "12px",
                flexWrap: "wrap",
                marginBottom: "12px",
              }}
            >
              <div>
                <h2 style={{ margin: 0, marginBottom: "8px" }}>Recent activity</h2>
                <p style={{ margin: 0, opacity: 0.8 }}>
                  Latest payments returned by the dashboard summary endpoint.
                </p>
              </div>

              <Link to="/payments/history" className="btn btn-secondary">
                View full history
              </Link>
            </div>

            {recentPayments.length === 0 ? (
              <div>
                <p style={{ marginBottom: "8px" }}>No recent activity yet.</p>
                <p style={{ marginTop: 0, opacity: 0.8 }}>
                  Start by sending a payment or creating a payment request.
                </p>

                <div style={{ marginTop: "12px", display: "flex", gap: "10px", flexWrap: "wrap" }}>
                  <Link to="/payments" className="btn btn-primary">
                    Send your first payment
                  </Link>
                  <Link to="/wallet" className="btn btn-secondary">
                    Open wallet
                  </Link>
                </div>
              </div>
            ) : (
              <div className="table-wrapper">
                <table className="table">
                  <thead>
                    <tr>
                      <th>Type</th>
                      <th>Counterparty</th>
                      <th>Amount</th>
                      <th>Status</th>
                      <th>Date</th>
                    </tr>
                  </thead>
                  <tbody>
                    {recentPayments.map((payment) => {
                      const isSent = payment.direction === "sent";
                      const type = isSent ? "Sent" : "Received";
                      const counterparty = isSent
                        ? `To @${payment.counterparty_username}`
                        : `From @${payment.counterparty_username}`;

                      return (
                        <tr
                          key={payment.id}
                          onClick={() => navigate(`/payments/${payment.id}`)}
                          style={{ cursor: "pointer" }}
                          title="View payment details"
                        >
                          <td>
                            <span
                              className={`badge ${
                                isSent ? "badge-info" : "badge-success"
                              }`}
                            >
                              {type}
                            </span>
                          </td>

                          <td>{counterparty}</td>

                          <td>
                            <strong>
                              {formatRelativeAmount(
                                payment.amount,
                                isSent,
                                wallet.currency
                              )}
                            </strong>
                          </td>

                          <td>
                            <span
                              className={`badge ${getStatusBadgeClass(payment.status)}`}
                            >
                              {payment.status}
                            </span>
                          </td>

                          <td>{formatDate(payment.created_at)}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </>
      )}
    </AppLayout>
  );
}

export default DashboardPage;