import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "../api/client";
import Layout from "../components/Layout";
import { formatCurrency, formatDate } from "../utils/formatters";

function WalletPage() {
  const [searchParams, setSearchParams] = useSearchParams();

  const [wallet, setWallet] = useState(null);
  const [transactions, setTransactions] = useState([]);
  const [transactionsCount, setTransactionsCount] = useState(0);

  const [loading, setLoading] = useState(true);
  const [transactionsLoading, setTransactionsLoading] = useState(true);
  const [submittingTopUp, setSubmittingTopUp] = useState(false);
  const [submittingWithdraw, setSubmittingWithdraw] = useState(false);

  const [topUpAmount, setTopUpAmount] = useState("");
  const [withdrawAmount, setWithdrawAmount] = useState("");

  const [topUpSuccessMessage, setTopUpSuccessMessage] = useState("");
  const [topUpErrorMessage, setTopUpErrorMessage] = useState("");
  const [withdrawSuccessMessage, setWithdrawSuccessMessage] = useState("");
  const [withdrawErrorMessage, setWithdrawErrorMessage] = useState("");
  const [pageError, setPageError] = useState("");

  const [transactionTypeFilter, setTransactionTypeFilter] = useState("all");
  const [transactionStatusFilter, setTransactionStatusFilter] = useState("all");
  const [transactionRailFilter, setTransactionRailFilter] = useState("all");

  const fetchWallet = async () => {
    const response = await api.get("/wallets/me/");
    setWallet(response.data);
  };

  const fetchTransactions = async () => {
    setTransactionsLoading(true);

    try {
      const response = await api.get("/wallets/me/transactions/", {
        params: {
          page: 1,
          page_size: 10,
          type: transactionTypeFilter,
          status: transactionStatusFilter,
          rail: transactionRailFilter,
        },
      });

      setTransactions(response.data.results);
      setTransactionsCount(response.data.count);
    } finally {
      setTransactionsLoading(false);
    }
  };

  const refreshWalletPage = async () => {
    await Promise.all([fetchWallet(), fetchTransactions()]);
  };

  useEffect(() => {
    async function loadWalletPage() {
      try {
        setLoading(true);
        setPageError("");
        await refreshWalletPage();
      } catch (error) {
        console.error("Error loading wallet page", error);
        setPageError("Could not load wallet data.");
      } finally {
        setLoading(false);
      }
    }

    loadWalletPage();
  }, []);

  useEffect(() => {
    if (!loading) {
      fetchTransactions().catch((error) => {
        console.error("Error loading filtered wallet transactions", error);
      });
    }
  }, [transactionTypeFilter, transactionStatusFilter, transactionRailFilter]);

  useEffect(() => {
    const topupStatus = searchParams.get("topup");

    if (!topupStatus || loading) {
      return;
    }

    const applyReturnState = async () => {
      clearMessages();

      try {
        await refreshWalletPage();

        if (topupStatus === "success") {
          setTopUpSuccessMessage(
            "Mercado Pago checkout finished successfully. Your top-up status was refreshed."
          );
        } else if (topupStatus === "pending") {
          setTopUpSuccessMessage(
            "Your top-up is still pending confirmation. We refreshed your wallet activity."
          );
        } else if (topupStatus === "failure") {
          setTopUpErrorMessage(
            "The Mercado Pago checkout did not complete successfully."
          );
        }
      } catch (error) {
        console.error("Error refreshing wallet after Mercado Pago return", error);
        setPageError("Could not refresh wallet data after checkout return.");
      } finally {
        const nextParams = new URLSearchParams(searchParams);
        nextParams.delete("topup");
        setSearchParams(nextParams, { replace: true });
      }
    };

    applyReturnState();
  }, [loading, searchParams, setSearchParams]);

  const getErrorMessage = (error, fallback) => {
    if (error.response?.data?.detail) return error.response.data.detail;
    if (error.response?.data?.error) return error.response.data.error;
    return fallback;
  };

  const clearMessages = () => {
    setTopUpSuccessMessage("");
    setTopUpErrorMessage("");
    setWithdrawSuccessMessage("");
    setWithdrawErrorMessage("");
  };

  const getTransactionBadgeClass = (transactionType) => {
    if (transactionType === "TOP_UP") return "badge-success";
    if (transactionType === "WITHDRAWAL") return "badge-error";
    return "badge-info";
  };

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

  const getStatusLabel = (status) => {
    if (status === "PENDING") return "Pending";
    if (status === "COMPLETED") return "Completed";
    if (status === "FAILED") return "Failed";
    return status || "-";
  };

  const getTransactionHeadline = (transaction) => {
    if (transaction.transaction_type === "TOP_UP") {
      return "Wallet funding";
    }

    if (transaction.transaction_type === "WITHDRAWAL") {
      return "Wallet withdrawal";
    }

    return "Wallet movement";
  };

  const transactionSummary = useMemo(() => {
    const summary = {
      pending: 0,
      completed: 0,
      failed: 0,
    };

    for (const transaction of transactions) {
      if (transaction.status === "PENDING") summary.pending += 1;
      if (transaction.status === "COMPLETED") summary.completed += 1;
      if (transaction.status === "FAILED") summary.failed += 1;
    }

    return summary;
  }, [transactions]);

  const handleTopUpSubmit = async (e) => {
    e.preventDefault();

    clearMessages();

    if (!topUpAmount) {
      setTopUpErrorMessage("Amount required.");
      return;
    }

    try {
      setSubmittingTopUp(true);

      const response = await api.post("/wallets/me/top-up-intents/", {
        amount: topUpAmount,
        rail: "MERCADO_PAGO",
      });

      const walletTransaction = response.data;

      setTopUpAmount("");
      await refreshWalletPage();

      if (walletTransaction.checkout_url) {
        window.location.href = walletTransaction.checkout_url;
        return;
      }

      setTopUpSuccessMessage("Top-up intent created successfully.");
    } catch (error) {
      console.error("WALLET TOP UP INTENT ERROR:", error);
      setTopUpErrorMessage(
        getErrorMessage(error, "Could not create top-up intent.")
      );
    } finally {
      setSubmittingTopUp(false);
    }
  };

  const handleWithdrawSubmit = async (e) => {
    e.preventDefault();

    clearMessages();

    if (!withdrawAmount) {
      setWithdrawErrorMessage("Amount required.");
      return;
    }

    try {
      setSubmittingWithdraw(true);

      await api.post("/wallets/me/withdraw/", {
        amount: withdrawAmount,
      });

      setWithdrawSuccessMessage("Withdrawal completed successfully.");
      setWithdrawAmount("");
      await refreshWalletPage();
    } catch (error) {
      console.error("WALLET WITHDRAW ERROR:", error);
      setWithdrawErrorMessage(
        getErrorMessage(error, "Could not withdraw funds.")
      );
    } finally {
      setSubmittingWithdraw(false);
    }
  };

  return (
    <Layout
      title="Wallet"
      subtitle="Manage your balance, start real top-ups through Mercado Pago, and review wallet funding activity."
    >
      {pageError && <div className="message message-error">{pageError}</div>}

      {loading && !pageError && <p>Loading wallet...</p>}

      {!loading && wallet && (
        <>
          <div className="grid grid-3" style={{ marginBottom: "18px" }}>
            <div className="card stat-card">
              <h3>Available balance</h3>
              <p className="stat-value">
                {formatCurrency(wallet.balance, wallet.currency)}
              </p>
              <p style={{ marginTop: "8px", opacity: 0.8 }}>
                Current wallet balance in {wallet.currency}.
              </p>
            </div>

            <div className="card stat-card">
              <h3>Funding rails</h3>
              <p style={{ margin: "8px 0 10px" }}>
                <span className="badge badge-info">Mercado Pago checkout</span>
              </p>
              <p style={{ margin: 0, opacity: 0.8 }}>
                Real top-up intents can be initiated from this page.
              </p>
            </div>

            <div className="card stat-card">
              <h3>Wallet owner</h3>
              <p className="stat-value" style={{ fontSize: "1.35rem" }}>
                #{wallet.user}
              </p>
              <p style={{ marginTop: "8px", opacity: 0.8 }}>
                Internal user reference linked to this wallet.
              </p>
            </div>
          </div>

          <div className="grid grid-2">
            <div className="card">
              <p className="eyebrow">Real funding flow</p>
              <h2>Add funds</h2>
              <p style={{ marginTop: 0, opacity: 0.8 }}>
                Create a real top-up intent, generate the external checkout, and
                continue through Mercado Pago.
              </p>

              <form onSubmit={handleTopUpSubmit}>
                <div className="form-group">
                  <label className="label">Amount</label>
                  <input
                    className="input"
                    type="number"
                    step="0.01"
                    min="0"
                    value={topUpAmount}
                    onChange={(e) => setTopUpAmount(e.target.value)}
                    placeholder="100.00"
                  />
                </div>

                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={submittingTopUp}
                >
                  {submittingTopUp ? "Creating intent..." : "Add funds"}
                </button>
              </form>

              {topUpSuccessMessage && (
                <div className="message message-success">
                  {topUpSuccessMessage}
                </div>
              )}

              {topUpErrorMessage && (
                <div className="message message-error">
                  {topUpErrorMessage}
                </div>
              )}
            </div>

            <div className="card">
              <p className="eyebrow">Sandbox operation</p>
              <h2>Withdraw funds</h2>
              <p style={{ marginTop: 0, opacity: 0.8 }}>
                Simulate money leaving the wallet through the current sandbox
                withdrawal flow.
              </p>

              <form onSubmit={handleWithdrawSubmit}>
                <div className="form-group">
                  <label className="label">Amount</label>
                  <input
                    className="input"
                    type="number"
                    step="0.01"
                    min="0"
                    value={withdrawAmount}
                    onChange={(e) => setWithdrawAmount(e.target.value)}
                    placeholder="50.00"
                  />
                </div>

                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={submittingWithdraw}
                >
                  {submittingWithdraw ? "Processing withdrawal..." : "Withdraw funds"}
                </button>
              </form>

              {withdrawSuccessMessage && (
                <div className="message message-success">
                  {withdrawSuccessMessage}
                </div>
              )}

              {withdrawErrorMessage && (
                <div className="message message-error">
                  {withdrawErrorMessage}
                </div>
              )}
            </div>
          </div>

          <div
            className="grid grid-3"
            style={{ marginTop: "18px", marginBottom: "18px" }}
          >
            <div className="card">
              <h3 style={{ marginTop: 0 }}>Pending in current view</h3>
              <p className="stat-value" style={{ fontSize: "1.7rem" }}>
                {transactionSummary.pending}
              </p>
              <p style={{ margin: 0, opacity: 0.8 }}>
                Funding operations still waiting for terminal resolution.
              </p>
            </div>

            <div className="card">
              <h3 style={{ marginTop: 0 }}>Completed in current view</h3>
              <p className="stat-value" style={{ fontSize: "1.7rem" }}>
                {transactionSummary.completed}
              </p>
              <p style={{ margin: 0, opacity: 0.8 }}>
                Operations already settled successfully.
              </p>
            </div>

            <div className="card">
              <h3 style={{ marginTop: 0 }}>Failed in current view</h3>
              <p className="stat-value" style={{ fontSize: "1.7rem" }}>
                {transactionSummary.failed}
              </p>
              <p style={{ margin: 0, opacity: 0.8 }}>
                Operations that ended with a failure state.
              </p>
            </div>
          </div>

          <div className="card">
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                gap: "12px",
                flexWrap: "wrap",
                alignItems: "flex-start",
                marginBottom: "14px",
              }}
            >
              <div>
                <h2 style={{ marginBottom: "8px" }}>Wallet funding activity</h2>
                <p style={{ margin: 0, opacity: 0.8 }}>
                  Review recent top-ups and withdrawals. Total matching records:{" "}
                  {transactionsCount}.
                </p>
              </div>

              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => refreshWalletPage()}
                disabled={transactionsLoading}
              >
                Refresh
              </button>
            </div>

            <div className="grid grid-3" style={{ marginBottom: "16px" }}>
              <div className="form-group">
                <label className="label">Type</label>
                <select
                  className="input"
                  value={transactionTypeFilter}
                  onChange={(e) => setTransactionTypeFilter(e.target.value)}
                >
                  <option value="all">All</option>
                  <option value="TOP_UP">TOP_UP</option>
                  <option value="WITHDRAWAL">WITHDRAWAL</option>
                </select>
              </div>

              <div className="form-group">
                <label className="label">Status</label>
                <select
                  className="input"
                  value={transactionStatusFilter}
                  onChange={(e) => setTransactionStatusFilter(e.target.value)}
                >
                  <option value="all">All</option>
                  <option value="PENDING">PENDING</option>
                  <option value="COMPLETED">COMPLETED</option>
                  <option value="FAILED">FAILED</option>
                </select>
              </div>

              <div className="form-group">
                <label className="label">Rail</label>
                <select
                  className="input"
                  value={transactionRailFilter}
                  onChange={(e) => setTransactionRailFilter(e.target.value)}
                >
                  <option value="all">All</option>
                  <option value="SANDBOX">SANDBOX</option>
                  <option value="MERCADO_PAGO">MERCADO_PAGO</option>
                  <option value="CARD">CARD</option>
                  <option value="BANK_TRANSFER">BANK_TRANSFER</option>
                </select>
              </div>
            </div>

            {transactionsLoading ? (
              <p>Loading wallet transactions...</p>
            ) : transactions.length === 0 ? (
              <div>
                <p style={{ marginBottom: "8px" }}>
                  No wallet transactions found for the selected filters.
                </p>
                <p style={{ margin: 0, opacity: 0.8 }}>
                  Try widening the filters or create a new funding operation.
                </p>
              </div>
            ) : (
              <div className="table-wrapper">
                <table className="table">
                  <thead>
                    <tr>
                      <th>Operation</th>
                      <th>Amount</th>
                      <th>Status</th>
                      <th>Rail</th>
                      <th>Provider status</th>
                      <th>Failure reason</th>
                      <th>Checkout</th>
                      <th>Created at</th>
                      <th>Detail</th>
                    </tr>
                  </thead>
                  <tbody>
                    {transactions.map((transaction) => (
                      <tr key={transaction.id}>
                        <td>
                          <div style={{ display: "grid", gap: "8px" }}>
                            <strong>{getTransactionHeadline(transaction)}</strong>
                            <div>
                              <span
                                className={`badge ${getTransactionBadgeClass(
                                  transaction.transaction_type
                                )}`}
                              >
                                {transaction.transaction_type}
                              </span>
                            </div>
                          </div>
                        </td>

                        <td>{formatCurrency(transaction.amount, wallet.currency)}</td>

                        <td>
                          <span
                            className={`badge ${getStatusBadgeClass(transaction.status)}`}
                          >
                            {getStatusLabel(transaction.status)}
                          </span>
                        </td>

                        <td>
                          <span className={`badge ${getRailBadgeClass(transaction.rail)}`}>
                            {transaction.rail}
                          </span>
                        </td>

                        <td>{transaction.provider_status || "-"}</td>

                        <td>{transaction.failure_reason || "-"}</td>

                        <td>
                          {transaction.checkout_url ? (
                            <a
                              href={transaction.checkout_url}
                              target="_blank"
                              rel="noreferrer"
                            >
                              Open checkout
                            </a>
                          ) : (
                            "-"
                          )}
                        </td>

                        <td>{formatDate(transaction.created_at)}</td>

                        <td>
                          <Link to={`/wallet/transactions/${transaction.id}`}>
                            View detail
                          </Link>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </>
      )}
    </Layout>
  );
}

export default WalletPage;