import { useState } from "react";
import type { DiaryEntry } from "../types/api";

interface EntryCardProps {
  entry: DiaryEntry;
  readOnly: boolean;
  onSave: (entryId: string, content: string) => Promise<void>;
  onDelete: (entryId: string) => Promise<void>;
  onValidationError: (message: string) => void;
}

export function EntryCard({
  entry,
  readOnly,
  onSave,
  onDelete,
  onValidationError,
}: EntryCardProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [draftContent, setDraftContent] = useState(entry.content);
  const [isSaving, setIsSaving] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  const handleStartEdit = () => {
    setDraftContent(entry.content);
    setIsEditing(true);
  };

  const handleCancelEdit = () => {
    setDraftContent(entry.content);
    setIsEditing(false);
  };

  const handleSave = async () => {
    const trimmed = draftContent.trim();
    if (!trimmed) {
      onValidationError("Content cannot be empty");
      return;
    }

    setIsSaving(true);
    try {
      await onSave(entry.entryId, trimmed);
      setIsEditing(false);
    } finally {
      setIsSaving(false);
    }
  };

  const handleDelete = async () => {
    setIsDeleting(true);
    try {
      await onDelete(entry.entryId);
    } finally {
      setIsDeleting(false);
    }
  };

  const locationLabel = entry.location?.city?.trim() || "";
  const temp = entry.weather?.temperature;
  const condition = entry.weather?.weather?.trim() || "";
  const weatherParts = [
    typeof temp === "number" ? `${Math.round(temp)}°C` : "",
    condition,
  ].filter(Boolean);
  const weatherLabel = weatherParts.join(" ");

  return (
    <div className="card mb-3 overflow-hidden">
      <div className="row g-0">
        <div className="col-md-4">
          {entry.imageUrl ? (
            <img
              src={entry.imageUrl}
              className="img-fluid h-100 w-100 entry-image-clickable"
              alt="Entry image"
              onClick={() => window.open(entry.imageUrl!, "_blank", "noopener,noreferrer")}
            />
          ) : (
            <div className="h-100 d-flex align-items-center justify-content-center bg-secondary-subtle text-muted small p-3">
              Image unavailable
            </div>
          )}
        </div>
        <div className="col-md-8">
          <div className="card-body">
            <div className="d-flex justify-content-between align-items-center mb-2">
              <small className="text-muted">
                {new Date(entry.createdAt).toLocaleString(undefined, {
                  dateStyle: "medium",
                  timeStyle: "short",
                })}
              </small>
              {entry.mode === "manual" && (
                <span className="badge rounded-pill ss-badge-sage">Edited</span>
              )}
            </div>

            {(locationLabel || weatherLabel) && (
              <div className="text-muted small d-flex flex-wrap gap-3 mb-2">
                {locationLabel && (
                  <span>
                    <i className="bi bi-geo-alt me-1" />
                    {locationLabel}
                  </span>
                )}
                {weatherLabel && (
                  <span>
                    <i className="bi bi-cloud-sun me-1" />
                    {weatherLabel}
                  </span>
                )}
              </div>
            )}

            {isEditing && !readOnly ? (
              <div className="mb-2">
                <div className="mb-3">
                  <textarea
                    className="form-control"
                    rows={4}
                    value={draftContent}
                    onChange={(e) => setDraftContent(e.target.value)}
                    disabled={isSaving}
                  />
                </div>
                <div className="d-flex gap-2">
                  <button
                    type="button"
                    className="btn btn-primary btn-sm"
                    disabled={isSaving}
                    onClick={handleSave}
                  >
                    {isSaving ? (
                      <>
                        <span className="spinner-border spinner-border-sm me-2" />
                        Saving...
                      </>
                    ) : (
                      "Save"
                    )}
                  </button>
                  <button
                    type="button"
                    className="btn btn-outline-secondary btn-sm"
                    disabled={isSaving}
                    onClick={handleCancelEdit}
                  >
                    Cancel
                  </button>
                </div>
              </div>
            ) : (
              <p className="card-text ss-entry-text mb-3">{entry.content}</p>
            )}

            {entry.editedAt && !isEditing && (
              <p className="card-text mb-2">
                <small className="text-muted">
                  Last edited:{" "}
                  {new Date(entry.editedAt).toLocaleString(undefined, {
                    dateStyle: "medium",
                    timeStyle: "short",
                  })}
                </small>
              </p>
            )}

            {!readOnly && !isEditing && (
              <div className="d-flex gap-2">
                <button
                  type="button"
                  className="btn btn-sm btn-outline-secondary"
                  disabled={isDeleting}
                  onClick={handleStartEdit}
                >
                  Edit
                </button>
                <button
                  type="button"
                  className="btn btn-sm btn-outline-danger"
                  disabled={isDeleting}
                  onClick={handleDelete}
                >
                  {isDeleting ? "Deleting..." : "Delete"}
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
