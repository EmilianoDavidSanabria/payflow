import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";
import Layout from "../components/Layout";
import {
  formatCurrency,
  formatDate,
  formatRelativeAmount,
} from "../utils/formatters";

function PaymentDetailPage() {
  const { id } = useParams();

  const [payment, setPayment] = useState(null);
  const [wallet, setWallet] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchPaymentData() {
      try {
        setLoading(true);
        setError("");

        const [paymentResponse, walletResponse] = await Promise.all([
          api.get(`/payments/${id}/`),
          api.get("/wallets/me/"),
        ]);

        setPayment(paymentResponse.data);
        setWallet(walletResponse.data);
      } catch (error) {
        console.error("PAYMENT DETAIL ERROR:", error);
        setError("Could not load payment.");
      } finally {
        setLoading(false);
      }
    }

    fetchPaymentData();
  }, [id]);

  const getStatusBadgeClass = (status) => {
    if (status === "COMPLETED") return "badge-success";
    if (status === "PENDING") return "badge-info";
    if (status === "FAILED") return "badge-error";
    return "badge-info";
  };

  return (
    <Layout
      title="Payment Details"
      subtitle={`Payment ID: ${id}`}
    >
      {error && <div className="message message-error">{error}</div>}

      {loading && !error && <p>Loading payment...</p>}

      {payment && wallet && (
        <>
          <div className="card" style={{ marginBottom: "18px" }}>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "flex-start",
                gap: "1rem",
                flexWrap: "wrap",
              }}
            >
              <div>
                <p style={{ margin: 0, fontSize: "0.95rem", opacity: 0.8 }}>
                  {wallet.user === payment.sender
                    ? "You sent this payment."
                    : "You received this payment."}
                </p>

                <h2
                  style={{
                    marginTop: "0.5rem",
                    marginBottom: "0.5rem",
                    fontSize: "2rem",
                  }}
                >
                  {formatRelativeAmount(
                    payment.amount,
                    wallet.user === payment.sender,
                    wallet.currency
                  )}
                </h2>

                <div
                  style={{
                    display: "flex",
                    gap: "0.5rem",
                    flexWrap: "wrap",
                  }}
                >
                  <span
                    className={`badge ${
                      wallet.user === payment.sender ? "badge-info" : "badge-success"
                    }`}
                  >
                    {wallet.user === payment.sender ? "Sent" : "Received"}
                  </span>

                  <span className={`badge ${getStatusBadgeClass(payment.status)}`}>
                    {payment.status}
                  </span>
                </div>
              </div>

              <div>
                <Link to="/payments/history" className="btn btn-secondary">
                  Back to history
                </Link>
              </div>
            </div>
          </div>

          <div className="grid grid-2">
            <div className="card">
              <p className="eyebrow">Summary</p>
              <h2>Payment overview</h2>

              <p>
                <strong>Amount:</strong> {formatCurrency(payment.amount, wallet.currency)}
              </p>

              <p>
                <strong>From:</strong> @{payment.sender_username}
              </p>

              <p>
                <strong>To:</strong> @{payment.receiver_username}
              </p>

              <p>
                <strong>Created at:</strong> {formatDate(payment.created_at)}
              </p>
            </div>

            <div className="card">
              <p className="eyebrow">Reference</p>
              <h2>Transaction data</h2>

              <p>
                <strong>Payment ID:</strong> {payment.id}
              </p>

              <p>
                <strong>Status:</strong>{" "}
                <span className={`badge ${getStatusBadgeClass(payment.status)}`}>
                  {payment.status}
                </span>
              </p>

              <p>
                <strong>Idempotency key:</strong>
              </p>

              <p style={{ wordBreak: "break-all", marginTop: "-0.25rem" }}>
                {payment.idempotency_key}
              </p>
            </div>
          </div>

          <div className="card" style={{ marginTop: "18px" }}>
            <h2>Actions</h2>
            <div
              style={{
                display: "flex",
                gap: "0.75rem",
                flexWrap: "wrap",
                marginTop: "0.75rem",
              }}
            >
              <Link to="/payments/history" className="btn btn-secondary">
                View full history
              </Link>

              <Link to="/payments" className="btn btn-primary">
                Send another payment
              </Link>
            </div>
          </div>
        </>
      )}
    </Layout>
  );
}

export default PaymentDetailPage;