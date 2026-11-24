export type AlertVariant = "success" | "danger" | "warning" | "info";

export interface AlertState {
  message: string;
  variant: AlertVariant;
}

interface AlertBannerProps {
  alert: AlertState | null;
  onDismiss: () => void;
}

export function AlertBanner({ alert, onDismiss }: AlertBannerProps) {
  if (!alert) {
    return null;
  }

  return (
    <div className={`alert alert-${alert.variant} alert-dismissible fade show`} role="alert">
      {alert.message}
      <button
        type="button"
        className="btn-close"
        aria-label="Close"
        onClick={onDismiss}
      />
    </div>
  );
}
