import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";
import AppLayout from "../components/AppLayout.jsx";
import { formatCurrency, formatDate } from "../utils/formatters";

function PaymentRequestDetailPage() {
  const { id } = useParams();

  const [paymentRequest, setPaymentRequest] = useState(null);
  const [wallet, setWallet] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchPaymentRequestData() {
      try {
        setLoading(true);
        setError("");

        const [requestResponse, walletResponse] = await Promise.all([
          api.get(`/payments/requests/${id}/`),
          api.get("/wallets/me/"),
        ]);

        setPaymentRequest(requestResponse.data);
        setWallet(walletResponse.data);
      } catch (error) {
        console.error("PAYMENT REQUEST DETAIL ERROR:", error);
        setError("Could not load payment request.");
      } finally {
        setLoading(false);
      }
    }

    fetchPaymentRequestData();
  }, [id]);

  const getStatusBadgeClass = (status) => {
    if (status === "ACCEPTED") return "badge-success";
    if (status === "PENDING") return "badge-info";
    if (status === "REJECTED") return "badge-error";
    return "badge-info";
  };

  const getDirectionLabel = (direction) => {
    if (direction === "outgoing") return "Outgoing request";
    if (direction === "incoming") return "Incoming request";
    return "Payment request";
  };

  const getHeadlineText = () => {
    if (!paymentRequest) return "";

    if (paymentRequest.direction === "outgoing") {
      return "You created this payment request.";
    }

    if (paymentRequest.direction === "incoming") {
      return "This payment request was sent to you.";
    }

    return "Payment request details.";
  };

  const getLinkedPaymentText = () => {
    if (!paymentRequest) return "";

    if (paymentRequest.status === "ACCEPTED" && paymentRequest.accepted_payment_id) {
      return `This request was completed through payment #${paymentRequest.accepted_payment_id}.`;
    }

    if (paymentRequest.status === "PENDING") {
      return "This request has not been completed yet.";
    }

    if (paymentRequest.status === "REJECTED") {
      return "This request was rejected, so no payment was created.";
    }

    return "No payment linked yet.";
  };

  return (
    <Layout title="Payment Request Details" subtitle={`Request ID: ${id}`}>
      {error && <div className="message message-error">{error}</div>}

      {loading && !error && <p>Loading payment request...</p>}

      {!loading && paymentRequest && wallet && (
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
                  {getHeadlineText()}
                </p>

                <h2
                  style={{
                    marginTop: "0.5rem",
                    marginBottom: "0.5rem",
                    fontSize: "2rem",
                  }}
                >
                  {formatCurrency(paymentRequest.amount, wallet.currency)}
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
                      paymentRequest.direction === "outgoing"
                        ? "badge-info"
                        : "badge-success"
                    }`}
                  >
                    {getDirectionLabel(paymentRequest.direction)}
                  </span>

                  <span className={`badge ${getStatusBadgeClass(paymentRequest.status)}`}>
                    {paymentRequest.status}
                  </span>
                </div>
              </div>

              <div>
                <Link to="/payments" className="btn btn-secondary">
                  Back to payments
                </Link>
              </div>
            </div>
          </div>

          <div className="grid grid-2">
            <div className="card">
              <p className="eyebrow">Summary</p>
              <h2>Request overview</h2>

              <p>
                <strong>Amount:</strong> {formatCurrency(paymentRequest.amount, wallet.currency)}
              </p>

              <p>
                <strong>Requester:</strong> @{paymentRequest.requester_username}
              </p>

              <p>
                <strong>Requested from:</strong> @{paymentRequest.requested_from_username}
              </p>

              <p>
                <strong>Direction:</strong> {getDirectionLabel(paymentRequest.direction)}
              </p>

              <p>
                <strong>Counterparty:</strong> @{paymentRequest.counterparty_username}
              </p>
            </div>

            <div className="card">
              <p className="eyebrow">Timeline</p>
              <h2>Request lifecycle</h2>

              <p>
                <strong>Created at:</strong> {formatDate(paymentRequest.created_at)}
              </p>

              <p>
                <strong>Updated at:</strong> {formatDate(paymentRequest.updated_at)}
              </p>

              <p>
                <strong>Resolved at:</strong>{" "}
                {paymentRequest.resolved_at
                  ? formatDate(paymentRequest.resolved_at)
                  : "Not resolved yet"}
              </p>

              <p>
                <strong>Status:</strong>{" "}
                <span className={`badge ${getStatusBadgeClass(paymentRequest.status)}`}>
                  {paymentRequest.status}
                </span>
              </p>
            </div>
          </div>

          <div className="card" style={{ marginTop: "18px" }}>
            <p className="eyebrow">Linked payment</p>
            <h2>Resolution result</h2>

            <p>{getLinkedPaymentText()}</p>

            {paymentRequest.accepted_payment_id && (
              <div
                style={{
                  display: "flex",
                  gap: "0.75rem",
                  flexWrap: "wrap",
                  marginTop: "0.75rem",
                }}
              >
                <Link
                  to={`/payments/${paymentRequest.accepted_payment_id}`}
                  className="btn btn-primary"
                >
                  View linked payment
                </Link>
              </div>
            )}
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
              <Link to="/payments" className="btn btn-secondary">
                Back to payments
              </Link>

              {paymentRequest.accepted_payment_id && (
                <Link
                  to={`/payments/${paymentRequest.accepted_payment_id}`}
                  className="btn btn-primary"
                >
                  Open linked payment
                </Link>
              )}
            </div>
          </div>
        </>
      )}
    </Layout>
  );
}

export default PaymentRequestDetailPage;