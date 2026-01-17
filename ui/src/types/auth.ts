export interface User {
  id: string;
  email: string;
  name?: string;
  profile?: UserProfile;
}

export interface UserProfile {
  show_quick_start: boolean;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  user: User;
  token?: string;
}
