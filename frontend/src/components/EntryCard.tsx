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

  return (
    <div className="card mb-3">
      <div className="row g-0">
        <div className="col-md-4">
          {entry.imageUrl ? (
            <img
              src={entry.imageUrl}
              className="img-fluid rounded-start entry-image-clickable"
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
                <div className="btn-group btn-group-sm">
                  <button
                    type="button"
                    className="btn btn-success"
                    disabled={isSaving}
                    onClick={handleSave}
                  >
                    {isSaving ? (
                      <>
                        <span className="spinner-border spinner-border-sm me-2" />
                        Loading...
                      </>
                    ) : (
                      "Save"
                    )}
                  </button>
                  <button
                    type="button"
                    className="btn btn-secondary"
                    disabled={isSaving}
                    onClick={handleCancelEdit}
                  >
                    Cancel
                  </button>
                </div>
              </div>
            ) : (
              <p className="card-text">{entry.content}</p>
            )}

            <p className="card-text">
              <small className="text-muted">
                {new Date(entry.createdAt).toLocaleString()}
                {entry.mode === "manual" && (
                  <span className="badge bg-info ms-2">Edited</span>
                )}
                {entry.editedAt && (
                  <>
                    <br />
                    Last edited: {new Date(entry.editedAt).toLocaleString()}
                  </>
                )}
              </small>
            </p>

            {!readOnly && !isEditing && (
              <div className="d-flex gap-1">
                <button
                  type="button"
                  className="btn btn-sm btn-primary"
                  disabled={isDeleting}
                  onClick={handleStartEdit}
                >
                  Edit
                </button>
                <button
                  type="button"
                  className="btn btn-sm btn-danger"
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
