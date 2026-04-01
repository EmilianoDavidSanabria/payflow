import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";
import AppLayout from "../components/AppLayout.jsx";
import { formatCurrency, formatDate } from "../utils/formatters";

function WalletTransactionDetailPage() {
  const { id } = useParams();

  const [walletTransaction, setWalletTransaction] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshingStatus, setRefreshingStatus] = useState(false);
  const [pageError, setPageError] = useState("");
  const [statusSuccessMessage, setStatusSuccessMessage] = useState("");
  const [statusErrorMessage, setStatusErrorMessage] = useState("");

  const loadWalletTransaction = async () => {
    const response = await api.get(`/wallets/me/transactions/${id}/`);
    setWalletTransaction(response.data);
    return response.data;
  };

  useEffect(() => {
    async function loadInitialWalletTransaction() {
      try {
        setLoading(true);
        setPageError("");
        setStatusSuccessMessage("");
        setStatusErrorMessage("");
        await loadWalletTransaction();
      } catch (error) {
        console.error("Error loading wallet transaction detail", error);

        if (error.response?.status === 404) {
          setPageError("Wallet transaction not found.");
        } else {
          setPageError("Could not load wallet transaction detail.");
        }
      } finally {
        setLoading(false);
      }
    }

    loadInitialWalletTransaction();
  }, [id]);

  const getStatusBadgeClass = (status) => {
    if (status === "COMPLETED") return "badge-success";
    if (status === "FAILED") return "badge-error";
    return "badge-info";
  };

  const getRailBadgeClass = (rail) => {
    if (rail === "MERCADO_PAGO") return "badge-info";
    if (rail === "SANDBOX") return "badge-success";
    return "badge-info";
  };

  const getTransactionBadgeClass = (transactionType) => {
    if (transactionType === "TOP_UP") return "badge-success";
    if (transactionType === "WITHDRAWAL") return "badge-error";
    return "badge-info";
  };

  const getStatusLabel = (status) => {
    if (status === "PENDING") return "Pending";
    if (status === "COMPLETED") return "Completed";
    if (status === "FAILED") return "Failed";
    return status || "-";
  };

  const headline = useMemo(() => {
    if (!walletTransaction) return "Wallet transaction";

    if (walletTransaction.transaction_type === "TOP_UP") {
      return "Wallet funding detail";
    }

    if (walletTransaction.transaction_type === "WITHDRAWAL") {
      return "Wallet withdrawal detail";
    }

    return "Wallet transaction detail";
  }, [walletTransaction]);

  const amountPrefix = walletTransaction?.transaction_type === "WITHDRAWAL" ? "-" : "+";

  const getErrorMessage = (error, fallback) => {
    if (error.response?.data?.detail) return error.response.data.detail;
    if (error.response?.data?.error) return error.response.data.error;
    return fallback;
  };

  const handleRefreshStatus = async () => {
    try {
      setRefreshingStatus(true);
      setStatusSuccessMessage("");
      setStatusErrorMessage("");

      const previousStatus = walletTransaction?.status;
      const previousProviderStatus = walletTransaction?.provider_status;

      const response = await api.post(
        `/wallets/me/transactions/${id}/refresh-status/`
      );

      const refreshedTransaction = response.data;
      setWalletTransaction(refreshedTransaction);

      if (
        previousStatus !== refreshedTransaction.status ||
        previousProviderStatus !== refreshedTransaction.provider_status
      ) {
        if (refreshedTransaction.status === "COMPLETED") {
          setStatusSuccessMessage(
            "Transaction status refreshed successfully. The top-up is now completed."
          );
        } else if (refreshedTransaction.status === "FAILED") {
          setStatusErrorMessage(
            "Transaction status refreshed. The top-up finished in a failed state."
          );
        } else {
          setStatusSuccessMessage(
            "Transaction status refreshed successfully."
          );
        }
      } else {
        setStatusSuccessMessage(
          "Transaction status checked. No changes were detected yet."
        );
      }
    } catch (error) {
      console.error("Error refreshing wallet transaction status", error);
      setStatusErrorMessage(
        getErrorMessage(error, "Could not refresh wallet transaction status.")
      );
    } finally {
      setRefreshingStatus(false);
    }
  };

  return (
    <Layout
      title="Wallet transaction detail"
      subtitle="Review the full state, timestamps, provider data, and checkout context for a wallet funding operation."
    >
      {pageError && <div className="message message-error">{pageError}</div>}

      {loading && !pageError && <p>Loading wallet transaction detail...</p>}

      {!loading && walletTransaction && (
        <>
          <div
            style={{
              marginBottom: "18px",
              display: "flex",
              gap: "12px",
              flexWrap: "wrap",
            }}
          >
            <Link to="/wallet" className="btn btn-secondary">
              Back to wallet
            </Link>

            {walletTransaction.status === "PENDING" &&
              walletTransaction.transaction_type === "TOP_UP" &&
              walletTransaction.rail === "MERCADO_PAGO" && (
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={handleRefreshStatus}
                  disabled={refreshingStatus}
                >
                  {refreshingStatus ? "Refreshing status..." : "Refresh status"}
                </button>
              )}
          </div>

          {statusSuccessMessage && (
            <div className="message message-success" style={{ marginBottom: "18px" }}>
              {statusSuccessMessage}
            </div>
          )}

          {statusErrorMessage && (
            <div className="message message-error" style={{ marginBottom: "18px" }}>
              {statusErrorMessage}
            </div>
          )}

          <div className="card" style={{ marginBottom: "18px" }}>
            <p className="eyebrow">{headline}</p>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                gap: "16px",
                alignItems: "flex-start",
                flexWrap: "wrap",
              }}
            >
              <div>
                <h2 style={{ marginBottom: "8px" }}>
                  {amountPrefix}
                  {formatCurrency(walletTransaction.amount)}
                </h2>

                <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
                  <span
                    className={`badge ${getTransactionBadgeClass(
                      walletTransaction.transaction_type
                    )}`}
                  >
                    {walletTransaction.transaction_type}
                  </span>

                  <span
                    className={`badge ${getStatusBadgeClass(walletTransaction.status)}`}
                  >
                    {getStatusLabel(walletTransaction.status)}
                  </span>

                  <span className={`badge ${getRailBadgeClass(walletTransaction.rail)}`}>
                    {walletTransaction.rail}
                  </span>
                </div>
              </div>

              <div style={{ minWidth: "220px" }}>
                <p style={{ margin: 0, opacity: 0.8 }}>Wallet transaction ID</p>
                <strong>#{walletTransaction.id}</strong>
              </div>
            </div>
          </div>

          {walletTransaction.status === "FAILED" && walletTransaction.failure_reason && (
            <div className="message message-error" style={{ marginBottom: "18px" }}>
              This operation failed with provider reason:{" "}
              <strong>{walletTransaction.failure_reason}</strong>
            </div>
          )}

          {walletTransaction.can_resume_checkout && walletTransaction.checkout_url && (
            <div className="message message-success" style={{ marginBottom: "18px" }}>
              This top-up is still pending and has an available checkout session.{" "}
              <a
                href={walletTransaction.checkout_url}
                target="_blank"
                rel="noreferrer"
              >
                Continue checkout
              </a>
            </div>
          )}

          <div className="grid grid-2">
            <div className="card">
              <h3 style={{ marginTop: 0 }}>Transaction state</h3>

              <div style={{ display: "grid", gap: "12px" }}>
                <div>
                  <strong>Transaction type</strong>
                  <p style={{ margin: "4px 0 0" }}>{walletTransaction.transaction_type}</p>
                </div>

                <div>
                  <strong>Status</strong>
                  <p style={{ margin: "4px 0 0" }}>{walletTransaction.status}</p>
                </div>

                <div>
                  <strong>Rail</strong>
                  <p style={{ margin: "4px 0 0" }}>{walletTransaction.rail}</p>
                </div>

                <div>
                  <strong>Provider status</strong>
                  <p style={{ margin: "4px 0 0" }}>
                    {walletTransaction.provider_status || "-"}
                  </p>
                </div>

                <div>
                  <strong>Failure reason</strong>
                  <p style={{ margin: "4px 0 0" }}>
                    {walletTransaction.failure_reason || "-"}
                  </p>
                </div>
              </div>
            </div>

            <div className="card">
              <h3 style={{ marginTop: 0 }}>References and timestamps</h3>

              <div style={{ display: "grid", gap: "12px" }}>
                <div>
                  <strong>Wallet ID</strong>
                  <p style={{ margin: "4px 0 0" }}>{walletTransaction.wallet_id}</p>
                </div>

                <div>
                  <strong>External reference</strong>
                  <p style={{ margin: "4px 0 0", wordBreak: "break-word" }}>
                    {walletTransaction.external_reference || "-"}
                  </p>
                </div>

                <div>
                  <strong>Created at</strong>
                  <p style={{ margin: "4px 0 0" }}>
                    {formatDate(walletTransaction.created_at)}
                  </p>
                </div>

                <div>
                  <strong>Updated at</strong>
                  <p style={{ margin: "4px 0 0" }}>
                    {formatDate(walletTransaction.updated_at)}
                  </p>
                </div>

                <div>
                  <strong>Completed at</strong>
                  <p style={{ margin: "4px 0 0" }}>
                    {walletTransaction.completed_at
                      ? formatDate(walletTransaction.completed_at)
                      : "-"}
                  </p>
                </div>
              </div>
            </div>
          </div>

          <div className="card" style={{ marginTop: "18px" }}>
            <h3 style={{ marginTop: 0 }}>Checkout context</h3>
            <p style={{ opacity: 0.8 }}>
              If this funding operation still depends on an external checkout session,
              you can inspect or continue it from here.
            </p>

            {walletTransaction.checkout_url ? (
              <a
                href={walletTransaction.checkout_url}
                target="_blank"
                rel="noreferrer"
              >
                Open external checkout
              </a>
            ) : (
              <p style={{ marginBottom: 0 }}>
                No external checkout is associated with this transaction.
              </p>
            )}
          </div>
        </>
      )}
    </Layout>
  );
}

export default WalletTransactionDetailPage;