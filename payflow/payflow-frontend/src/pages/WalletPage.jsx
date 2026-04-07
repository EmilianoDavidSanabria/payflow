import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api, getApiErrorMessage } from "../api/client";
import AppLayout from "../components/AppLayout.jsx";
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
  const [refreshingPage, setRefreshingPage] = useState(false);

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
    return response.data;
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

      setTransactions(response.data.results || []);
      setTransactionsCount(response.data.count || 0);
      return response.data;
    } finally {
      setTransactionsLoading(false);
    }
  };

  const refreshWalletPage = async () => {
    await Promise.all([fetchWallet(), fetchTransactions()]);
  };

  const clearMessages = () => {
    setTopUpSuccessMessage("");
    setTopUpErrorMessage("");
    setWithdrawSuccessMessage("");
    setWithdrawErrorMessage("");
    setPageError("");
  };

  const isValidPositiveAmount = (value) => {
    const parsed = Number(value);
    return Number.isFinite(parsed) && parsed > 0;
  };

  useEffect(() => {
    async function loadWalletPage() {
      try {
        setLoading(true);
        setPageError("");
        await refreshWalletPage();
      } catch (error) {
        console.error("Error loading wallet page", error);
        setPageError(
          getApiErrorMessage(error, "Could not load your wallet information.")
        );
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
        setPageError(
          getApiErrorMessage(
            error,
            "Could not refresh wallet transactions for the selected filters."
          )
        );
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
        setRefreshingPage(true);
        await refreshWalletPage();

        if (topupStatus === "success") {
          setTopUpSuccessMessage(
            "Your Mercado Pago checkout finished. We refreshed your wallet activity so you can verify whether the funds were already credited."
          );
        } else if (topupStatus === "pending") {
          setTopUpSuccessMessage(
            "Your payment is still being confirmed. The transaction may remain pending for a short time before it is credited."
          );
        } else if (topupStatus === "failure") {
          setTopUpErrorMessage(
            "The checkout did not finish successfully. You can review the transaction below and try again if needed."
          );
        }
      } catch (error) {
        console.error("Error refreshing wallet after Mercado Pago return", error);
        setPageError(
          getApiErrorMessage(
            error,
            "Could not refresh wallet data after returning from checkout."
          )
        );
      } finally {
        setRefreshingPage(false);
        const nextParams = new URLSearchParams(searchParams);
        nextParams.delete("topup");
        setSearchParams(nextParams, { replace: true });
      }
    };

    applyReturnState();
  }, [loading, searchParams, setSearchParams]);

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
    if (status === "PENDING") return "Pending confirmation";
    if (status === "COMPLETED") return "Completed";
    if (status === "FAILED") return "Failed";
    return status || "-";
  };

  const getProviderStatusLabel = (providerStatus) => {
    if (!providerStatus) return "-";
    if (providerStatus === "CHECKOUT_CREATED") return "Checkout created";
    if (providerStatus === "approved") return "Approved by provider";
    if (providerStatus === "pending") return "Pending at provider";
    if (providerStatus === "in_process") return "Processing at provider";
    if (providerStatus === "rejected") return "Rejected by provider";
    if (providerStatus === "cancelled") return "Cancelled";
    return providerStatus;
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

  const getTransactionHint = (transaction) => {
    if (transaction.status === "PENDING" && transaction.rail === "MERCADO_PAGO") {
      return "Waiting for confirmation from Mercado Pago.";
    }

    if (transaction.status === "COMPLETED" && transaction.transaction_type === "TOP_UP") {
      return "Funds were credited to your wallet.";
    }

    if (
      transaction.status === "COMPLETED" &&
      transaction.transaction_type === "WITHDRAWAL"
    ) {
      return "Funds were removed from your wallet.";
    }

    if (transaction.status === "FAILED") {
      return "The operation ended in a failed state.";
    }

    return "Review the detail page for full context.";
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

  const pendingMercadoPagoTopUps = useMemo(() => {
    return transactions.filter(
      (transaction) =>
        transaction.transaction_type === "TOP_UP" &&
        transaction.rail === "MERCADO_PAGO" &&
        transaction.status === "PENDING"
    );
  }, [transactions]);

  const handleTopUpSubmit = async (e) => {
    e.preventDefault();
    clearMessages();

    if (!isValidPositiveAmount(topUpAmount)) {
      setTopUpErrorMessage("Enter a valid amount greater than 0.");
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
        setTopUpSuccessMessage(
          "Top-up intent created. Redirecting you to Mercado Pago checkout..."
        );
        window.location.href = walletTransaction.checkout_url;
        return;
      }

      setTopUpSuccessMessage(
        "Top-up intent created successfully. Review its status in the activity list below."
      );
    } catch (error) {
      console.error("WALLET TOP UP INTENT ERROR:", error);
      setTopUpErrorMessage(
        getApiErrorMessage(error, "Could not create the top-up intent.")
      );
    } finally {
      setSubmittingTopUp(false);
    }
  };

  const handleWithdrawSubmit = async (e) => {
    e.preventDefault();
    clearMessages();

    if (!isValidPositiveAmount(withdrawAmount)) {
      setWithdrawErrorMessage("Enter a valid amount greater than 0.");
      return;
    }

    try {
      setSubmittingWithdraw(true);

      await api.post("/wallets/me/withdraw/", {
        amount: withdrawAmount,
      });

      setWithdrawSuccessMessage(
        "Withdrawal completed successfully and your wallet balance was updated."
      );
      setWithdrawAmount("");
      await refreshWalletPage();
    } catch (error) {
      console.error("WALLET WITHDRAW ERROR:", error);
      setWithdrawErrorMessage(
        getApiErrorMessage(error, "Could not complete the withdrawal.")
      );
    } finally {
      setSubmittingWithdraw(false);
    }
  };

  const handleManualRefresh = async () => {
    try {
      setRefreshingPage(true);
      setPageError("");
      await refreshWalletPage();
    } catch (error) {
      console.error("Error refreshing wallet page", error);
      setPageError(
        getApiErrorMessage(error, "Could not refresh wallet information.")
      );
    } finally {
      setRefreshingPage(false);
    }
  };

  return (
    <AppLayout
      title="Wallet"
      subtitle="Manage your balance, add funds through Mercado Pago, and review the current status of your wallet activity."
    >
      {pageError && <div className="message message-error">{pageError}</div>}

      {loading && !pageError && <p>Loading wallet...</p>}

      {!loading && wallet && (
        <>
          {pendingMercadoPagoTopUps.length > 0 && (
            <div className="message message-success" style={{ marginBottom: "18px" }}>
              You have <strong>{pendingMercadoPagoTopUps.length}</strong> Mercado Pago
              top-up{pendingMercadoPagoTopUps.length > 1 ? "s" : ""} still waiting for
              confirmation. Open the detail page to continue checkout or refresh the
              status.
            </div>
          )}

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
              <h3>Funding rail</h3>
              <p style={{ margin: "8px 0 10px" }}>
                <span className="badge badge-info">Mercado Pago checkout</span>
              </p>
              <p style={{ margin: 0, opacity: 0.8 }}>
                Real top-ups are created here and then confirmed asynchronously.
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
                Create a real top-up intent and continue in Mercado Pago checkout. The
                final credit may take a moment to be confirmed.
              </p>

              <form onSubmit={handleTopUpSubmit}>
                <div className="form-group">
                  <label className="label">
                    Amount ({wallet?.currency || "ARS"})
                  </label>
                  <input
                    className="input"
                    type="number"
                    step="0.01"
                    min="0"
                    value={topUpAmount}
                    onChange={(e) => setTopUpAmount(e.target.value)}
                    placeholder={wallet?.currency === "ARS" ? "1000.00" : "10.00"}
                    disabled={submittingTopUp}
                  />
                </div>

                <p style={{ marginTop: "8px", marginBottom: "16px", opacity: 0.8 }}>
                  After creating the intent, you will be redirected to Mercado Pago to
                  complete the payment.
                </p>

                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={submittingTopUp}
                >
                  {submittingTopUp ? "Creating checkout..." : "Add funds"}
                </button>
              </form>

              {topUpSuccessMessage && (
                <div className="message message-success">{topUpSuccessMessage}</div>
              )}

              {topUpErrorMessage && (
                <div className="message message-error">{topUpErrorMessage}</div>
              )}
            </div>

            <div className="card">
              <p className="eyebrow">Sandbox operation</p>
              <h2>Withdraw funds</h2>
              <p style={{ marginTop: 0, opacity: 0.8 }}>
                Simulate money leaving the wallet through the current sandbox withdrawal
                flow.
              </p>

              <form onSubmit={handleWithdrawSubmit}>
                <div className="form-group">
                  <label className="label">
                    Amount ({wallet?.currency || "ARS"})
                  </label>
                  <input
                    className="input"
                    type="number"
                    step="0.01"
                    min="0"
                    value={withdrawAmount}
                    onChange={(e) => setWithdrawAmount(e.target.value)}
                    placeholder={wallet?.currency === "ARS" ? "1000.00" : "10.00"}
                    disabled={submittingWithdraw}
                  />
                </div>

                <p style={{ marginTop: "8px", marginBottom: "16px", opacity: 0.8 }}>
                  Withdrawals are processed immediately in the current sandbox flow.
                </p>

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
                <div className="message message-error">{withdrawErrorMessage}</div>
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
                Operations still waiting for final confirmation.
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
                Operations that ended in a failed state.
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
                  Review recent top-ups and withdrawals. Matching records:{" "}
                  {transactionsCount}.
                </p>
              </div>

              <button
                type="button"
                className="btn btn-secondary"
                onClick={handleManualRefresh}
                disabled={transactionsLoading || refreshingPage}
              >
                {refreshingPage ? "Refreshing..." : "Refresh"}
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
                  No wallet transactions match the selected filters.
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
                      <th>Created at</th>
                      <th>Next step</th>
                      <th>Detail</th>
                    </tr>
                  </thead>
                  <tbody>
                    {transactions.map((transaction) => {
                      const canContinueCheckout =
                        transaction.status === "PENDING" &&
                        transaction.transaction_type === "TOP_UP" &&
                        transaction.rail === "MERCADO_PAGO" &&
                        !!transaction.checkout_url;

                      return (
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
                              <small style={{ opacity: 0.75 }}>
                                {getTransactionHint(transaction)}
                              </small>
                            </div>
                          </td>

                          <td>{formatCurrency(transaction.amount, wallet.currency)}</td>

                          <td>
                            <span
                              className={`badge ${getStatusBadgeClass(
                                transaction.status
                              )}`}
                            >
                              {getStatusLabel(transaction.status)}
                            </span>
                          </td>

                          <td>
                            <span
                              className={`badge ${getRailBadgeClass(transaction.rail)}`}
                            >
                              {transaction.rail}
                            </span>
                          </td>

                          <td>{getProviderStatusLabel(transaction.provider_status)}</td>

                          <td>{transaction.failure_reason || "-"}</td>

                          <td>{formatDate(transaction.created_at)}</td>

                          <td>
                            {canContinueCheckout ? (
                              <a
                                href={transaction.checkout_url}
                                target="_blank"
                                rel="noreferrer"
                              >
                                Continue checkout
                              </a>
                            ) : transaction.status === "PENDING" ? (
                              "Wait or refresh detail"
                            ) : transaction.status === "FAILED" ? (
                              "Review failure"
                            ) : (
                              "Completed"
                            )}
                          </td>

                          <td>
                            <Link to={`/wallet/transactions/${transaction.id}`}>
                              View detail
                            </Link>
                          </td>
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

export default WalletPage;