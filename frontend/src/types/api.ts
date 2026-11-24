export type UserRole = "user" | "admin";

export interface AuthUser {
  userId: string;
  email: string;
  displayName: string | null;
  role: UserRole;
}

export interface User extends AuthUser {
  createdAt: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: AuthUser;
}

export interface Photo {
  userId: string;
  photoId: string;
  filePath: string;
  photoUrl: string | null;
  createdAt: string;
}

export interface UploadPhotoResponse {
  photoId: string;
  photoUrl: string | null;
}

export interface EntryLocation {
  city?: string | null;
  region?: string | null;
  country?: string | null;
}

export interface EntryWeather {
  weather?: string | null;
  temperature?: number | null;
}

export interface DiaryEntry {
  entryId: string;
  userId: string;
  content: string;
  imageUrl: string | null;
  location: EntryLocation | null;
  weather: EntryWeather | null;
  mode: string;
  createdAt: string;
  editedAt: string | null;
}

export interface GenerateEntryResponse {
  status: string;
  diary_entry: DiaryEntry;
  photo_id: string;
}

export interface RegisterPayload {
  email: string;
  password: string;
  displayName: string;
}
