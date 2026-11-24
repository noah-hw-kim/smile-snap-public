import type { Photo } from "../types/api";

interface PhotoListProps {
  photos: Photo[];
  loading: boolean;
  readOnly: boolean;
  generatingPhotoId: string | null;
  deletingPhotoId: string | null;
  onGenerate: (photoId: string) => void;
  onDelete: (photoId: string) => void;
}

export function PhotoList({
  photos,
  loading,
  readOnly,
  generatingPhotoId,
  deletingPhotoId,
  onGenerate,
  onDelete,
}: PhotoListProps) {
  if (loading) {
    return <p className="text-muted mb-0">Loading photos...</p>;
  }

  if (photos.length === 0) {
    return <p className="text-muted mb-0">No photos uploaded yet.</p>;
  }

  const openPhoto = (url: string | null) => {
    if (url) {
      window.open(url, "_blank", "noopener,noreferrer");
    }
  };

  return (
    <div className="list-group list-group-flush">
      {photos.map((photo) => {
        const isGenerating = generatingPhotoId === photo.photoId;
        const isDeleting = deletingPhotoId === photo.photoId;

        return (
          <div
            key={photo.photoId}
            className="list-group-item d-flex justify-content-between align-items-center photo-item px-2"
            onClick={() => openPhoto(photo.photoUrl)}
          >
            {photo.photoUrl ? (
              <img
                src={photo.photoUrl}
                alt="Screenshot"
                className="me-3 rounded photo-thumbnail"
              />
            ) : (
              <div className="me-3 rounded bg-secondary-subtle d-flex align-items-center justify-content-center photo-thumbnail text-muted small">
                N/A
              </div>
            )}
            <span className="flex-grow-1 small text-muted">
              {new Date(photo.createdAt).toLocaleString(undefined, {
                dateStyle: "medium",
                timeStyle: "short",
              })}
            </span>
            {!readOnly && (
              <div
                className="d-flex gap-2"
                onClick={(e) => e.stopPropagation()}
              >
                <button
                  type="button"
                  className="btn btn-sm btn-primary"
                  disabled={isGenerating || isDeleting}
                  onClick={() => onGenerate(photo.photoId)}
                >
                  {isGenerating ? (
                    <>
                      <span className="spinner-border spinner-border-sm me-2" />
                      Writing...
                    </>
                  ) : (
                    "Generate"
                  )}
                </button>
                <button
                  type="button"
                  className="btn btn-sm btn-outline-danger"
                  disabled={isGenerating || isDeleting}
                  onClick={() => onDelete(photo.photoId)}
                >
                  {isDeleting ? "Deleting..." : "Delete"}
                </button>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
