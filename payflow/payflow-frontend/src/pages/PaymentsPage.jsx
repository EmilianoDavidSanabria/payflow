import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api, getApiErrorMessage } from "../api/client";
import AppLayout from "../components/AppLayout.jsx";
import ConfirmPaymentModal from "../components/ConfirmPaymentModal";
import { formatCurrency, formatDate } from "../utils/formatters";
import UserSearchInput from "../components/UserSearchInput";

function PaymentsPage() {
  const [receiverUsername, setReceiverUsername] = useState("");
  const [amount, setAmount] = useState("");
  const [successMessage, setSuccessMessage] = useState("");
  const [errorMessage, setErrorMessage] = useState("");
  const [paymentData, setPaymentData] = useState(null);
  const [showConfirm, setShowConfirm] = useState(false);
  const [submittingPayment, setSubmittingPayment] = useState(false);

  const [requestUsername, setRequestUsername] = useState("");
  const [requestAmount, setRequestAmount] = useState("");
  const [requestSuccessMessage, setRequestSuccessMessage] = useState("");
  const [requestErrorMessage, setRequestErrorMessage] = useState("");
  const [submittingRequest, setSubmittingRequest] = useState(false);

  const [recentRecipients, setRecentRecipients] = useState([]);
  const [loadingRecentRecipients, setLoadingRecentRecipients] = useState(true);

  const [frequentRecipients, setFrequentRecipients] = useState([]);
  const [loadingFrequentRecipients, setLoadingFrequentRecipients] = useState(true);

  const [incomingRequests, setIncomingRequests] = useState([]);
  const [outgoingRequests, setOutgoingRequests] = useState([]);
  const [loadingRequests, setLoadingRequests] = useState(true);
  const [requestActionLoadingId, setRequestActionLoadingId] = useState(null);

  const [requestHistory, setRequestHistory] = useState([]);
  const [requestHistoryCount, setRequestHistoryCount] = useState(0);
  const [requestHistoryPage, setRequestHistoryPage] = useState(1);
  const [requestHistoryTotalPages, setRequestHistoryTotalPages] = useState(1);
  const [loadingRequestHistory, setLoadingRequestHistory] = useState(true);
  const [requestHistoryError, setRequestHistoryError] = useState("");

  const [requestHistoryFilters, setRequestHistoryFilters] = useState({
    type: "all",
    status: "all",
    username: "",
    date_from: "",
    date_to: "",
  });

  const clearPaymentMessages = () => {
    setSuccessMessage("");
    setErrorMessage("");
  };

  const clearRequestMessages = () => {
    setRequestSuccessMessage("");
    setRequestErrorMessage("");
  };

  useEffect(() => {
    const fetchRecentRecipients = async () => {
      try {
        const response = await api.get("/payments/recent-recipients/");
        setRecentRecipients(response.data);
      } catch (error) {
        console.error("RECENT RECIPIENTS ERROR:", error);
      } finally {
        setLoadingRecentRecipients(false);
      }
    };

    const fetchFrequentRecipients = async () => {
      try {
        const response = await api.get("/payments/frequent-recipients/");
        setFrequentRecipients(response.data);
      } catch (error) {
        console.error("FREQUENT RECIPIENTS ERROR:", error);
      } finally {
        setLoadingFrequentRecipients(false);
      }
    };

    fetchRecentRecipients();
    fetchFrequentRecipients();
  }, []);

  useEffect(() => {
    const fetchPendingRequests = async () => {
      try {
        const [incomingResponse, outgoingResponse] = await Promise.all([
          api.get("/payments/requests/", {
            params: { type: "incoming", status: "PENDING", page_size: 5 },
          }),
          api.get("/payments/requests/", {
            params: { type: "outgoing", status: "PENDING", page_size: 5 },
          }),
        ]);

        setIncomingRequests(incomingResponse.data.results);
        setOutgoingRequests(outgoingResponse.data.results);
      } catch (error) {
        console.error("PAYMENT REQUESTS ERROR:", error);
      } finally {
        setLoadingRequests(false);
      }
    };

    fetchPendingRequests();
  }, []);

  useEffect(() => {
    const fetchRequestHistory = async () => {
      setLoadingRequestHistory(true);
      setRequestHistoryError("");

      try {
        const response = await api.get("/payments/requests/", {
          params: {
            ...requestHistoryFilters,
            page: requestHistoryPage,
            page_size: 10,
          },
        });

        setRequestHistory(response.data.results);
        setRequestHistoryCount(response.data.count);
        setRequestHistoryTotalPages(response.data.total_pages);
      } catch (error) {
        console.error("PAYMENT REQUEST HISTORY ERROR:", error);
        setRequestHistoryError(
          getApiErrorMessage(error, "Could not load payment request history.")
        );
      } finally {
        setLoadingRequestHistory(false);
      }
    };

    fetchRequestHistory();
  }, [requestHistoryFilters, requestHistoryPage]);

  const requestCounts = useMemo(
    () => ({
      incoming: incomingRequests.length,
      outgoing: outgoingRequests.length,
      history: requestHistoryCount,
    }),
    [incomingRequests.length, outgoingRequests.length, requestHistoryCount]
  );

  const refreshPaymentRequests = async () => {
    try {
      const [incomingResponse, outgoingResponse, historyResponse] = await Promise.all([
        api.get("/payments/requests/", {
          params: { type: "incoming", status: "PENDING", page_size: 5 },
        }),
        api.get("/payments/requests/", {
          params: { type: "outgoing", status: "PENDING", page_size: 5 },
        }),
        api.get("/payments/requests/", {
          params: {
            ...requestHistoryFilters,
            page: requestHistoryPage,
            page_size: 10,
          },
        }),
      ]);

      setIncomingRequests(incomingResponse.data.results);
      setOutgoingRequests(outgoingResponse.data.results);
      setRequestHistory(historyResponse.data.results);
      setRequestHistoryCount(historyResponse.data.count);
      setRequestHistoryTotalPages(historyResponse.data.total_pages);
    } catch (error) {
      console.error("REFRESH PAYMENT REQUESTS ERROR:", error);
    }
  };

  const getRequestStatusBadgeClass = (status) => {
    if (status === "ACCEPTED") return "badge-success";
    if (status === "REJECTED") return "badge-error";
    return "badge-info";
  };

  const handleSubmit = (e) => {
    e.preventDefault();

    clearPaymentMessages();

    if (!receiverUsername || !amount) {
      setErrorMessage("Select a receiver and enter an amount.");
      return;
    }

    setShowConfirm(true);
  };

  const confirmPayment = async () => {
    setShowConfirm(false);
    setPaymentData(null);
    clearPaymentMessages();

    try {
      setSubmittingPayment(true);

      const idempotencyKey = crypto.randomUUID();

      const response = await api.post(
        "/payments/create/",
        {
          receiver_username: receiverUsername,
          amount: amount,
        },
        {
          headers: {
            "Idempotency-Key": idempotencyKey,
          },
        }
      );

      setPaymentData(response.data);
      setSuccessMessage("Payment completed successfully.");

      const paidUsername = response.data.receiver_username;

      setReceiverUsername("");
      setAmount("");

      setRecentRecipients((prev) => {
        const filtered = prev.filter((item) => item.username !== paidUsername);

        return [
          {
            username: paidUsername,
            last_paid_at: new Date().toISOString(),
          },
          ...filtered,
        ].slice(0, 6);
      });

      setFrequentRecipients((prev) => {
        const existing = prev.find((item) => item.username === paidUsername);

        if (existing) {
          return [...prev]
            .map((item) =>
              item.username === paidUsername
                ? { ...item, payments_count: item.payments_count + 1 }
                : item
            )
            .sort((a, b) => {
              if (b.payments_count !== a.payments_count) {
                return b.payments_count - a.payments_count;
              }
              return a.username.localeCompare(b.username);
            })
            .slice(0, 6);
        }

        return [
          ...prev,
          {
            username: paidUsername,
            payments_count: 1,
          },
        ]
          .sort((a, b) => {
            if (b.payments_count !== a.payments_count) {
              return b.payments_count - a.payments_count;
            }
            return a.username.localeCompare(b.username);
          })
          .slice(0, 6);
      });

      await refreshPaymentRequests();
    } catch (error) {
      console.error("PAYMENT ERROR:", error);
      setErrorMessage(getApiErrorMessage(error, "Could not create payment."));
    } finally {
      setSubmittingPayment(false);
    }
  };

  const handleRequestSubmit = async (e) => {
    e.preventDefault();

    clearRequestMessages();

    if (!requestUsername || !requestAmount) {
      setRequestErrorMessage("Select a username and enter an amount.");
      return;
    }

    try {
      setSubmittingRequest(true);

      await api.post(
        "/payments/requests/create/",
        {
          requested_from_username: requestUsername,
          amount: requestAmount,
        },
        { headers: { "Content-Type": "application/json" } }
      );

      setRequestSuccessMessage("Payment request created successfully.");
      setRequestUsername("");
      setRequestAmount("");
      setRequestHistoryPage(1);
      await refreshPaymentRequests();
    } catch (error) {
      console.error("PAYMENT REQUEST CREATE ERROR:", error);
      setRequestErrorMessage(
        getApiErrorMessage(error, "Could not create payment request.")
      );
    } finally {
      setSubmittingRequest(false);
    }
  };

  const handleAcceptRequest = async (requestId) => {
    try {
      setRequestActionLoadingId(requestId);
      clearPaymentMessages();

      await api.post(`/payments/requests/${requestId}/accept/`);
      setSuccessMessage("Payment request accepted successfully.");
      await refreshPaymentRequests();
    } catch (error) {
      console.error("PAYMENT REQUEST ACCEPT ERROR:", error);
      setErrorMessage(
        getApiErrorMessage(error, "Could not accept payment request.")
      );
    } finally {
      setRequestActionLoadingId(null);
    }
  };

  const handleRejectRequest = async (requestId) => {
    try {
      setRequestActionLoadingId(requestId);
      clearRequestMessages();

      await api.post(`/payments/requests/${requestId}/reject/`);
      setRequestSuccessMessage("Payment request rejected.");
      await refreshPaymentRequests();
    } catch (error) {
      console.error("PAYMENT REQUEST REJECT ERROR:", error);
      setRequestErrorMessage(
        getApiErrorMessage(error, "Could not reject payment request.")
      );
    } finally {
      setRequestActionLoadingId(null);
    }
  };

  const handleRequestHistoryFilterChange = (field, value) => {
    setRequestHistoryPage(1);
    setRequestHistoryFilters((prev) => ({
      ...prev,
      [field]: value,
    }));
  };

  return (
    <AppLayout
      title="Payments"
      subtitle="Send money, request payments from other users, and manage pending payment requests."
    >
      <div className="grid grid-3" style={{ marginBottom: "18px" }}>
        <div className="card">
          <h3 style={{ marginTop: 0 }}>Incoming pending requests</h3>
          <p className="stat-value" style={{ fontSize: "1.7rem" }}>
            {requestCounts.incoming}
          </p>
          <p style={{ margin: 0, opacity: 0.8 }}>
            Requests waiting for your response.
          </p>
        </div>

        <div className="card">
          <h3 style={{ marginTop: 0 }}>Outgoing pending requests</h3>
          <p className="stat-value" style={{ fontSize: "1.7rem" }}>
            {requestCounts.outgoing}
          </p>
          <p style={{ margin: 0, opacity: 0.8 }}>
            Requests you created that are still unresolved.
          </p>
        </div>

        <div className="card">
          <h3 style={{ marginTop: 0 }}>Request history results</h3>
          <p className="stat-value" style={{ fontSize: "1.7rem" }}>
            {requestCounts.history}
          </p>
          <p style={{ margin: 0, opacity: 0.8 }}>
            Records matching the current request history filters.
          </p>
        </div>
      </div>

      <div className="grid grid-2">
        <div className="card">
          <p className="eyebrow">Money movement</p>
          <h2>Send payment</h2>
          <p style={{ marginTop: 0, opacity: 0.8 }}>
            Create a direct payment to another PayFlow user using the main payment flow.
          </p>

          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label className="label">Receiver username</label>
              <UserSearchInput
                value={receiverUsername}
                onSelect={(username) => setReceiverUsername(username)}
              />
            </div>

            {loadingFrequentRecipients ? (
              <div className="form-group">
                <label className="label">Frequent contacts</label>
                <p>Loading frequent contacts...</p>
              </div>
            ) : frequentRecipients.length > 0 ? (
              <div className="form-group">
                <label className="label">Frequent contacts</label>
                <div
                  style={{
                    display: "flex",
                    flexWrap: "wrap",
                    gap: "0.5rem",
                    marginTop: "0.5rem",
                  }}
                >
                  {frequentRecipients.map((recipient) => (
                    <button
                      key={recipient.username}
                      type="button"
                      className="btn btn-secondary"
                      onClick={() => setReceiverUsername(recipient.username)}
                      title={`${recipient.payments_count} payments`}
                    >
                      @{recipient.username}
                    </button>
                  ))}
                </div>
              </div>
            ) : null}

            {loadingRecentRecipients ? (
              <div className="form-group">
                <label className="label">Recent recipients</label>
                <p>Loading recent recipients...</p>
              </div>
            ) : recentRecipients.length > 0 ? (
              <div className="form-group">
                <label className="label">Recent recipients</label>
                <div
                  style={{
                    display: "flex",
                    flexWrap: "wrap",
                    gap: "0.5rem",
                    marginTop: "0.5rem",
                  }}
                >
                  {recentRecipients.map((recipient) => (
                    <button
                      key={recipient.username}
                      type="button"
                      className="btn btn-secondary"
                      onClick={() => setReceiverUsername(recipient.username)}
                      title={`Last paid: ${formatDate(recipient.last_paid_at)}`}
                    >
                      @{recipient.username}
                    </button>
                  ))}
                </div>
              </div>
            ) : null}

            <div className="form-group">
              <label className="label">Amount</label>
              <input
                className="input"
                type="number"
                step="0.01"
                min="0"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                placeholder="50.00"
              />
            </div>

            <p style={{ marginTop: "8px", marginBottom: "16px", opacity: 0.8 }}>
              Payments are created immediately and require confirmation before they are sent.
            </p>

            <button
              className="btn btn-primary"
              type="submit"
              disabled={submittingPayment}
            >
              {submittingPayment ? "Processing payment..." : "Send payment"}
            </button>
          </form>

          {successMessage && <div className="message message-success">{successMessage}</div>}
          {errorMessage && <div className="message message-error">{errorMessage}</div>}
        </div>

        <div className="card">
          <p className="eyebrow">Payment requests</p>
          <h2>Request payment</h2>
          <p style={{ marginTop: 0, opacity: 0.8 }}>
            Ask another PayFlow user to send you money and track the request lifecycle.
          </p>

          <form onSubmit={handleRequestSubmit}>
            <div className="form-group">
              <label className="label">Ask payment from</label>
              <UserSearchInput
                value={requestUsername}
                onSelect={(username) => setRequestUsername(username)}
              />
            </div>

            <div className="form-group">
              <label className="label">Amount</label>
              <input
                className="input"
                type="number"
                step="0.01"
                min="0"
                value={requestAmount}
                onChange={(e) => setRequestAmount(e.target.value)}
                placeholder="50.00"
              />
            </div>

            <p style={{ marginTop: "8px", marginBottom: "16px", opacity: 0.8 }}>
              The request stays pending until the other user accepts or rejects it.
            </p>

            <button
              className="btn btn-primary"
              type="submit"
              disabled={submittingRequest}
            >
              {submittingRequest ? "Creating request..." : "Create request"}
            </button>
          </form>

          {requestSuccessMessage && (
            <div className="message message-success">{requestSuccessMessage}</div>
          )}

          {requestErrorMessage && (
            <div className="message message-error">{requestErrorMessage}</div>
          )}
        </div>
      </div>

      <div className="grid grid-2" style={{ marginTop: "18px" }}>
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
              <h2 style={{ margin: 0 }}>Incoming requests</h2>
              <p style={{ margin: "8px 0 0", opacity: 0.8 }}>
                Pending requests that require your decision.
              </p>
            </div>
          </div>

          {loadingRequests ? (
            <p>Loading incoming requests...</p>
          ) : incomingRequests.length === 0 ? (
            <p>No pending incoming requests.</p>
          ) : (
            <div className="table-wrapper">
              <table className="table">
                <thead>
                  <tr>
                    <th>From</th>
                    <th>Amount</th>
                    <th>Date</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {incomingRequests.map((request) => (
                    <tr key={request.id}>
                      <td>
                        <Link to={`/payments/requests/${request.id}`}>
                          @{request.counterparty_username}
                        </Link>
                      </td>
                      <td>{formatCurrency(request.amount)}</td>
                      <td>{formatDate(request.created_at)}</td>
                      <td>
                        <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
                          <button
                            type="button"
                            className="btn btn-primary"
                            onClick={() => handleAcceptRequest(request.id)}
                            disabled={requestActionLoadingId === request.id}
                          >
                            {requestActionLoadingId === request.id ? "Processing..." : "Accept"}
                          </button>
                          <button
                            type="button"
                            className="btn btn-secondary"
                            onClick={() => handleRejectRequest(request.id)}
                            disabled={requestActionLoadingId === request.id}
                          >
                            Reject
                          </button>
                          <Link
                            to={`/payments/requests/${request.id}`}
                            className="btn btn-secondary"
                          >
                            View
                          </Link>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
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
              <h2 style={{ margin: 0 }}>Outgoing requests</h2>
              <p style={{ margin: "8px 0 0", opacity: 0.8 }}>
                Pending requests you created and are waiting on.
              </p>
            </div>
          </div>

          {loadingRequests ? (
            <p>Loading outgoing requests...</p>
          ) : outgoingRequests.length === 0 ? (
            <p>No pending outgoing requests.</p>
          ) : (
            <div className="table-wrapper">
              <table className="table">
                <thead>
                  <tr>
                    <th>To</th>
                    <th>Amount</th>
                    <th>Status</th>
                    <th>Date</th>
                    <th>Detail</th>
                  </tr>
                </thead>
                <tbody>
                  {outgoingRequests.map((request) => (
                    <tr key={request.id}>
                      <td>
                        <Link to={`/payments/requests/${request.id}`}>
                          @{request.counterparty_username}
                        </Link>
                      </td>
                      <td>{formatCurrency(request.amount)}</td>
                      <td>
                        <span className={`badge ${getRequestStatusBadgeClass(request.status)}`}>
                          {request.status}
                        </span>
                      </td>
                      <td>{formatDate(request.created_at)}</td>
                      <td>
                        <Link
                          to={`/payments/requests/${request.id}`}
                          className="btn btn-secondary"
                        >
                          View
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      <div className="card" style={{ marginTop: "18px" }}>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "flex-start",
            gap: "12px",
            flexWrap: "wrap",
            marginBottom: "12px",
          }}
        >
          <div>
            <p className="eyebrow">Search and review</p>
            <h2 style={{ margin: 0, marginBottom: "8px" }}>Payment request history</h2>
            <p style={{ margin: 0, opacity: 0.8 }}>
              Browse historical payment requests with filters for direction, status, user, and date range.
            </p>
          </div>
        </div>

        <div className="grid grid-2" style={{ marginBottom: "16px" }}>
          <div className="form-group">
            <label className="label">Type</label>
            <select
              className="input"
              value={requestHistoryFilters.type}
              onChange={(e) =>
                handleRequestHistoryFilterChange("type", e.target.value)
              }
            >
              <option value="all">All</option>
              <option value="incoming">Incoming</option>
              <option value="outgoing">Outgoing</option>
            </select>
          </div>

          <div className="form-group">
            <label className="label">Status</label>
            <select
              className="input"
              value={requestHistoryFilters.status}
              onChange={(e) =>
                handleRequestHistoryFilterChange("status", e.target.value)
              }
            >
              <option value="all">All</option>
              <option value="PENDING">Pending</option>
              <option value="ACCEPTED">Accepted</option>
              <option value="REJECTED">Rejected</option>
            </select>
          </div>

          <div className="form-group">
            <label className="label">Username</label>
            <input
              className="input"
              type="text"
              value={requestHistoryFilters.username}
              onChange={(e) =>
                handleRequestHistoryFilterChange("username", e.target.value)
              }
              placeholder="juan"
            />
          </div>

          <div className="form-group">
            <label className="label">Date from</label>
            <input
              className="input"
              type="date"
              value={requestHistoryFilters.date_from}
              onChange={(e) =>
                handleRequestHistoryFilterChange("date_from", e.target.value)
              }
            />
          </div>

          <div className="form-group">
            <label className="label">Date to</label>
            <input
              className="input"
              type="date"
              value={requestHistoryFilters.date_to}
              onChange={(e) =>
                handleRequestHistoryFilterChange("date_to", e.target.value)
              }
            />
          </div>
        </div>

        {requestHistoryError && (
          <div className="message message-error">{requestHistoryError}</div>
        )}

        {loadingRequestHistory ? (
          <p>Loading payment request history...</p>
        ) : requestHistory.length === 0 ? (
          <div>
            <p style={{ marginBottom: "8px" }}>
              No payment requests found for the selected filters.
            </p>
            <p style={{ margin: 0, opacity: 0.8 }}>
              Try changing the filters or create a new payment request.
            </p>
          </div>
        ) : (
          <>
            <div className="table-wrapper">
              <table className="table">
                <thead>
                  <tr>
                    <th>Type</th>
                    <th>Counterparty</th>
                    <th>Amount</th>
                    <th>Status</th>
                    <th>Date</th>
                    <th>Detail</th>
                  </tr>
                </thead>
                <tbody>
                  {requestHistory.map((request) => {
                    const isOutgoing = request.direction === "outgoing";

                    return (
                      <tr key={request.id}>
                        <td>
                          <span
                            className={`badge ${
                              isOutgoing ? "badge-info" : "badge-success"
                            }`}
                          >
                            {isOutgoing ? "Outgoing" : "Incoming"}
                          </span>
                        </td>
                        <td>
                          <Link to={`/payments/requests/${request.id}`}>
                            @{request.counterparty_username}
                          </Link>
                        </td>
                        <td>{formatCurrency(request.amount)}</td>
                        <td>
                          <span
                            className={`badge ${getRequestStatusBadgeClass(request.status)}`}
                          >
                            {request.status}
                          </span>
                        </td>
                        <td>{formatDate(request.created_at)}</td>
                        <td>
                          <Link
                            to={`/payments/requests/${request.id}`}
                            className="btn btn-secondary"
                          >
                            View
                          </Link>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                marginTop: "12px",
                gap: "12px",
                flexWrap: "wrap",
              }}
            >
              <p style={{ margin: 0 }}>
                Showing page {requestHistoryPage} of {requestHistoryTotalPages} ·{" "}
                {requestHistoryCount} result{requestHistoryCount === 1 ? "" : "s"}
              </p>

              <div style={{ display: "flex", gap: "0.5rem" }}>
                <button
                  type="button"
                  className="btn btn-secondary"
                  disabled={requestHistoryPage <= 1}
                  onClick={() =>
                    setRequestHistoryPage((prev) => Math.max(prev - 1, 1))
                  }
                >
                  Previous
                </button>

                <button
                  type="button"
                  className="btn btn-secondary"
                  disabled={requestHistoryPage >= requestHistoryTotalPages}
                  onClick={() =>
                    setRequestHistoryPage((prev) =>
                      Math.min(prev + 1, requestHistoryTotalPages)
                    )
                  }
                >
                  Next
                </button>
              </div>
            </div>
          </>
        )}
      </div>

      <div className="card" style={{ marginTop: "18px" }}>
        <p className="eyebrow">Latest result</p>
        <h2>Payment result</h2>

        {!paymentData ? (
          <p style={{ marginBottom: 0 }}>
            No payment created yet in this session.
          </p>
        ) : (
          <>
            <p>
              <strong>ID:</strong> {paymentData.id}
            </p>
            <p>
              <strong>Sender:</strong> @{paymentData.sender_username}
            </p>
            <p>
              <strong>Receiver:</strong> @{paymentData.receiver_username}
            </p>
            <p>
              <strong>Amount:</strong> {formatCurrency(paymentData.amount)}
            </p>
            <p>
              <strong>Status:</strong>{" "}
              <span className="badge badge-success">{paymentData.status}</span>
            </p>

            <div style={{ marginTop: "0.75rem" }}>
              <Link to={`/payments/${paymentData.id}`} className="btn btn-primary">
                View payment detail
              </Link>
            </div>
          </>
        )}
      </div>

      {showConfirm && (
        <ConfirmPaymentModal
          receiver={receiverUsername}
          amount={amount}
          onConfirm={confirmPayment}
          onCancel={() => setShowConfirm(false)}
        />
      )}
    </AppLayout>
  );
}

export default PaymentsPage;