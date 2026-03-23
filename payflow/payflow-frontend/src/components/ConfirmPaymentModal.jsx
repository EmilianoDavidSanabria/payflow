import { formatCurrency } from "../utils/formatters";

function ConfirmPaymentModal({ receiver, amount, onConfirm, onCancel }) {
  return (
    <div className="modal-overlay" role="dialog" aria-modal="true">
      <div className="modal">
        <p className="eyebrow">Payment confirmation</p>
        <h2>Confirm payment</h2>

        <p className="modal-text">
          You are about to send{" "}
          <strong>{formatCurrency(amount)}</strong> to{" "}
          <strong>@{receiver}</strong>.
        </p>

        <p className="modal-muted">
          This action will create a real payment in PayFlow.
        </p>

        <div className="modal-actions">
          <button type="button" className="btn btn-secondary" onClick={onCancel}>
            Cancel
          </button>

          <button type="button" className="btn btn-primary" onClick={onConfirm}>
            Confirm payment
          </button>
        </div>
      </div>
    </div>
  );
}

export default ConfirmPaymentModal;