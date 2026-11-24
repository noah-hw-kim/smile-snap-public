import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { api } from "../api/client";
import { AlertBanner, type AlertState } from "../components/AlertBanner";
import { EntryCard } from "../components/EntryCard";
import { Navbar } from "../components/Navbar";
import { PhotoList } from "../components/PhotoList";
import { useAuth } from "../context/AuthContext";
import type { DiaryEntry, Photo } from "../types/api";

const MAX_UPLOAD_BYTES = 10 * 1024 * 1024;

export function DashboardPage() {
  const { user, isAdmin, logout } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  const viewUserId = searchParams.get("viewUser");
  const isAdminReadOnly = isAdmin && Boolean(viewUserId);
  const targetUserId = isAdminReadOnly && viewUserId ? viewUserId : user?.userId ?? "";

  const [alert, setAlert] = useState<AlertState | null>(null);
  const [photos, setPhotos] = useState<Photo[]>([]);
  const [entries, setEntries] = useState<DiaryEntry[]>([]);
  const [loadingPhotos, setLoadingPhotos] = useState(true);
  const [loadingEntries, setLoadingEntries] = useState(true);

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const [generatingPhotoId, setGeneratingPhotoId] = useState<string | null>(null);
  const [deletingPhotoId, setDeletingPhotoId] = useState<string | null>(null);

  const fetchPhotos = useCallback(async () => {
    if (!targetUserId) return;
    setLoadingPhotos(true);
    try {
      const data = await api.getUserPhotos(targetUserId);
      setPhotos(data);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unknown error";
      setAlert({ message: `Failed to load photos: ${message}`, variant: "danger" });
    } finally {
      setLoadingPhotos(false);
    }
  }, [targetUserId]);

  const fetchEntries = useCallback(async () => {
    if (!targetUserId) return;
    setLoadingEntries(true);
    try {
      const data = await api.getUserEntries(targetUserId);
      setEntries(data);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unknown error";
      setAlert({ message: `Failed to load entries: ${message}`, variant: "danger" });
    } finally {
      setLoadingEntries(false);
    }
  }, [targetUserId]);

  useEffect(() => {
    void Promise.all([fetchPhotos(), fetchEntries()]);
  }, [fetchPhotos, fetchEntries]);

  const handleUpload = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!selectedFile) return;

    if (selectedFile.size > MAX_UPLOAD_BYTES) {
      setAlert({ message: "File too large (max 10MB)", variant: "warning" });
      return;
    }

    setIsUploading(true);
    try {
      await api.uploadPhoto(selectedFile);
      setAlert({ message: "Photo uploaded successfully!", variant: "success" });
      setSelectedFile(null);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
      await fetchPhotos();
    } catch (error) {
      const message = error instanceof Error ? error.message : "Upload failed";
      setAlert({ message, variant: "danger" });
    } finally {
      setIsUploading(false);
    }
  };

  const handleGenerate = async (photoId: string) => {
    setGeneratingPhotoId(photoId);
    try {
      await api.generateEntry(photoId);
      setAlert({ message: "Diary entry generated successfully!", variant: "success" });
      await fetchEntries();
    } catch (error) {
      const message = error instanceof Error ? error.message : "Generation failed";
      setAlert({ message, variant: "danger" });
    } finally {
      setGeneratingPhotoId(null);
    }
  };

  const handleDeletePhoto = async (photoId: string) => {
    if (!window.confirm("Delete this photo?")) return;
    setDeletingPhotoId(photoId);
    try {
      await api.deletePhoto(photoId);
      setAlert({ message: "Photo deleted successfully", variant: "info" });
      await fetchPhotos();
    } catch (error) {
      const message = error instanceof Error ? error.message : "Delete failed";
      setAlert({ message, variant: "danger" });
    } finally {
      setDeletingPhotoId(null);
    }
  };

  const handleSaveEntry = async (entryId: string, content: string) => {
    if (!user) return;
    try {
      await api.updateEntry(user.userId, entryId, content);
      setAlert({ message: "Entry updated successfully!", variant: "success" });
      await fetchEntries();
    } catch (error) {
      const message = error instanceof Error ? error.message : "Update failed";
      setAlert({ message, variant: "danger" });
      throw error;
    }
  };

  const handleDeleteEntry = async (entryId: string) => {
    if (!user || !window.confirm("Delete this diary entry?")) return;
    try {
      await api.deleteEntry(user.userId, entryId);
      setAlert({ message: "Entry deleted successfully", variant: "info" });
      await fetchEntries();
    } catch (error) {
      const message = error instanceof Error ? error.message : "Delete failed";
      setAlert({ message, variant: "danger" });
    }
  };

  const handleDeleteAccount = async () => {
    if (!user) return;
    const confirmMessage =
      `⚠️ WARNING: This action cannot be undone!\n\n` +
      `This will permanently delete:\n` +
      `- Your account (${user.email})\n` +
      `- All your photos\n` +
      `- All your diary entries\n` +
      `- All associated data\n\n` +
      `Type "DELETE" to confirm:`;

    const userInput = window.prompt(confirmMessage);
    if (userInput === "DELETE") {
      const finalConfirm = window.confirm(
        `Are you absolutely sure you want to delete your account "${user.email}"?\n\nThis action is PERMANENT and cannot be reversed.`
      );
      if (finalConfirm) {
        try {
          await api.deleteUser(user.userId);
          logout();
          navigate("/login", { replace: true });
        } catch {
          setAlert({
            message: "Failed to delete account. Please try again.",
            variant: "danger",
          });
        }
      }
    } else if (userInput !== null) {
      setAlert({
        message: 'Account deletion cancelled. You must type "DELETE" exactly.',
        variant: "warning",
      });
    }
  };

  const handleLogout = () => {
    logout();
    navigate("/login", { replace: true });
  };

  const subtitle = isAdminReadOnly
    ? "Admin viewing user data"
    : `${user?.role ?? "user"}: ${user?.email ?? ""}`;

  return (
    <>
      <Navbar
        title="📱 User Dashboard"
        subtitle={subtitle}
        showBackToAdmin={isAdminReadOnly}
        onLogout={handleLogout}
      />

      <div className="container mt-3">
        <AlertBanner alert={alert} onDismiss={() => setAlert(null)} />
      </div>

      <div className="container mt-4">
        {isAdminReadOnly ? (
          <div className="alert alert-info">
            <h5 className="mb-0">👁️ Viewing User Dashboard (Read Only)</h5>
          </div>
        ) : (
          <div className="card mb-4">
            <div className="card-header d-flex justify-content-between align-items-center">
              <h5 className="mb-0">📸 Upload Screenshot</h5>
            </div>
            <div className="card-body">
              <form onSubmit={handleUpload}>
                <div className="mb-3">
                  <label htmlFor="imageFile" className="form-label">
                    Select Image (Max 10MB)
                  </label>
                  <input
                    ref={fileInputRef}
                    type="file"
                    className="form-control"
                    id="imageFile"
                    accept="image/*"
                    onChange={(e) => setSelectedFile(e.target.files?.[0] ?? null)}
                    required
                  />
                </div>
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={isUploading}
                >
                  {isUploading ? (
                    <>
                      <span className="spinner-border spinner-border-sm me-2" />
                      Loading...
                    </>
                  ) : (
                    <>
                      <i className="bi bi-cloud-upload" /> Upload
                    </>
                  )}
                </button>
              </form>
            </div>
          </div>
        )}

        <div className="row">
          <div className="col-md-6">
            <div className="card">
              <div className="card-header d-flex justify-content-between align-items-center">
                <h5 className="mb-0">📷 My Photos</h5>
                <button
                  type="button"
                  className="btn btn-sm btn-outline-primary"
                  onClick={() => void fetchPhotos()}
                >
                  <i className="bi bi-arrow-clockwise" />
                </button>
              </div>
              <div className="card-body">
                <PhotoList
                  photos={photos}
                  loading={loadingPhotos}
                  readOnly={isAdminReadOnly}
                  generatingPhotoId={generatingPhotoId}
                  deletingPhotoId={deletingPhotoId}
                  onGenerate={(id) => void handleGenerate(id)}
                  onDelete={(id) => void handleDeletePhoto(id)}
                />
              </div>
            </div>
          </div>

          <div className="col-md-6">
            <div className="card">
              <div className="card-header d-flex justify-content-between align-items-center">
                <h5 className="mb-0">📖 Diary Entries</h5>
                <div className="d-flex align-items-center gap-2">
                  <small className="text-muted">{entries.length} entries</small>
                  <button
                    type="button"
                    className="btn btn-sm btn-outline-primary"
                    onClick={() => void fetchEntries()}
                  >
                    <i className="bi bi-arrow-clockwise" />
                  </button>
                </div>
              </div>
              <div className="card-body">
                {loadingEntries ? (
                  <p className="text-muted mb-0">Loading entries...</p>
                ) : entries.length === 0 ? (
                  <p className="text-muted mb-0">No diary entries yet.</p>
                ) : (
                  entries.map((entry) => (
                    <EntryCard
                      key={entry.entryId}
                      entry={entry}
                      readOnly={isAdminReadOnly}
                      onSave={handleSaveEntry}
                      onDelete={handleDeleteEntry}
                      onValidationError={(msg) =>
                        setAlert({ message: msg, variant: "warning" })
                      }
                    />
                  ))
                )}
              </div>
            </div>
          </div>
        </div>

        {!isAdminReadOnly && (
          <div className="row mt-4 mb-4">
            <div className="col-12">
              <div className="card border-danger">
                <div className="card-header bg-danger text-white">
                  <h6 className="mb-0">⚠️ Danger Zone</h6>
                </div>
                <div className="card-body">
                  <p className="text-muted mb-3">
                    Once you delete your account, there is no going back. Please be certain.
                  </p>
                  <button
                    type="button"
                    className="btn btn-danger"
                    onClick={() => void handleDeleteAccount()}
                  >
                    <i className="bi bi-trash" /> Delete My Account
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </>
  );
}
