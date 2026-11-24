import type {
  DiaryEntry,
  GenerateEntryResponse,
  LoginResponse,
  Photo,
  RegisterPayload,
  UploadPhotoResponse,
  User,
} from "../types/api";

const rawBaseUrl = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
export const API_BASE_URL = rawBaseUrl.replace(/\/+$/, "");

export class ApiError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export interface ApiRequestOptions extends RequestInit {
  token?: string | null;
  skipUnauthorizedHandler?: boolean;
}

let unauthorizedHandler: (() => void) | null = null;

export function registerUnauthorizedHandler(handler: (() => void) | null): void {
  unauthorizedHandler = handler;
}

function extractErrorMessage(bodyText: string, status: number): string {
  if (bodyText) {
    try {
      const parsed: unknown = JSON.parse(bodyText);
      if (parsed && typeof parsed === "object" && "detail" in parsed) {
        const detail = (parsed as { detail: unknown }).detail;
        if (typeof detail === "string" && detail.trim()) {
          return detail;
        }
        if (Array.isArray(detail) && detail.length > 0) {
          const messages = detail
            .map((item) =>
              item && typeof item === "object" && "msg" in item
                ? String((item as { msg: unknown }).msg)
                : ""
            )
            .filter(Boolean);
          if (messages.length > 0) {
            return messages.join("; ");
          }
        }
      }
    } catch {
      // Non-JSON response body (e.g. HTML 502 page); fall through to generic status message
    }
  }
  return `HTTP error! status: ${status}`;
}

export async function apiFetch<T>(
  endpoint: string,
  options: ApiRequestOptions = {}
): Promise<T> {
  const { token, skipUnauthorizedHandler = false, ...fetchInit } = options;
  const headers = new Headers(fetchInit.headers);
  const resolvedToken = token !== undefined ? token : localStorage.getItem("authToken");

  if (resolvedToken) {
    headers.set("Authorization", `Bearer ${resolvedToken}`);
  }

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...fetchInit,
      headers,
    });
  } catch (error) {
    if (error instanceof Error && error.message.includes("NetworkError")) {
      throw new ApiError("Backend not responding - check if server is running", 0);
    }
    throw error;
  }

  if (!response.ok) {
    const bodyText = await response.text();
    const message = extractErrorMessage(bodyText, response.status);
    if (response.status === 401 && !skipUnauthorizedHandler && unauthorizedHandler) {
      unauthorizedHandler();
    }
    throw new ApiError(message, response.status);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

export const api = {
  login(email: string, password: string): Promise<LoginResponse> {
    const formData = new FormData();
    formData.append("username", email);
    formData.append("password", password);
    return apiFetch<LoginResponse>("/token", {
      method: "POST",
      body: formData,
      token: null,
      skipUnauthorizedHandler: true,
    });
  },

  register(payload: RegisterPayload): Promise<User> {
    return apiFetch<User>("/users/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      token: null,
      skipUnauthorizedHandler: true,
    });
  },

  getUserPhotos(userId: string): Promise<Photo[]> {
    return apiFetch<Photo[]>(`/screenshots/user/${userId}`);
  },

  uploadPhoto(image: File): Promise<UploadPhotoResponse> {
    const formData = new FormData();
    formData.append("image", image);
    return apiFetch<UploadPhotoResponse>("/screenshots/upload", {
      method: "POST",
      body: formData,
    });
  },

  deletePhoto(photoId: string): Promise<void> {
    return apiFetch<void>(`/screenshots/${photoId}`, {
      method: "DELETE",
    });
  },

  generateEntry(photoId: string): Promise<GenerateEntryResponse> {
    return apiFetch<GenerateEntryResponse>(`/screenshots/${photoId}/generate`, {
      method: "POST",
    });
  },

  getUserEntries(userId: string): Promise<DiaryEntry[]> {
    return apiFetch<DiaryEntry[]>(`/users/${userId}/entries`);
  },

  updateEntry(userId: string, entryId: string, content: string): Promise<DiaryEntry> {
    return apiFetch<DiaryEntry>(`/users/${userId}/entries/${entryId}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content }),
    });
  },

  deleteEntry(userId: string, entryId: string): Promise<void> {
    return apiFetch<void>(`/users/${userId}/entries/${entryId}`, {
      method: "DELETE",
    });
  },

  deleteUser(userId: string): Promise<void> {
    return apiFetch<void>(`/users/${userId}`, {
      method: "DELETE",
    });
  },

  getAdminUsers(): Promise<User[]> {
    return apiFetch<User[]>("/admin/users");
  },
};
