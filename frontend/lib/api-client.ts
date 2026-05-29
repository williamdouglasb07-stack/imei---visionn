import axios, { AxiosInstance, AxiosRequestConfig } from 'axios';
import Cookie from 'js-cookie';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

class APIClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: API_URL,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Interceptor para adicionar token
    this.client.interceptors.request.use((config) => {
      const token = Cookie.get('access_token');
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      return config;
    });

    // Interceptor para erros
    this.client.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response?.status === 401) {
          // Limpar tokens e redirecionar para login
          Cookie.remove('access_token');
          Cookie.remove('refresh_token');
          window.location.href = '/login';
        }
        return Promise.reject(error);
      }
    );
  }

  // Auth
  async register(email: string, username: string, password: string, fullName?: string) {
    return this.client.post('/auth/register', {
      email,
      username,
      password,
      full_name: fullName,
    });
  }

  async login(email: string, password: string) {
    const response = await this.client.post('/auth/login', {
      email,
      password,
    });
    
    if (response.data.access_token) {
      Cookie.set('access_token', response.data.access_token, {
        expires: 1,
        secure: true,
        sameSite: 'strict',
      });
      Cookie.set('refresh_token', response.data.refresh_token, {
        expires: 7,
        secure: true,
        sameSite: 'strict',
      });
    }
    
    return response.data;
  }

  async refreshToken() {
    const refreshToken = Cookie.get('refresh_token');
    if (!refreshToken) throw new Error('No refresh token');
    
    const response = await this.client.post('/auth/refresh', {
      refresh_token: refreshToken,
    });
    
    Cookie.set('access_token', response.data.access_token);
    return response.data;
  }

  async getCurrentUser() {
    return this.client.get('/auth/me');
  }

  // Upload
  async uploadImages(files: File[]) {
    const formData = new FormData();
    files.forEach((file) => {
      formData.append('files', file);
    });

    return this.client.post('/upload/images', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  }

  async getImages(skip: number = 0, limit: number = 20) {
    return this.client.get('/upload/images', {
      params: { skip, limit },
    });
  }

  async getImageDetail(imageId: string) {
    return this.client.get(`/upload/images/${imageId}`);
  }

  async deleteImage(imageId: string) {
    return this.client.delete(`/upload/images/${imageId}`);
  }

  async downloadImage(imageId: string) {
    return this.client.get(`/upload/file/${imageId}`, {
      responseType: 'blob',
    });
  }

  // Search
  async searchIMEIs(query: string, searchType: 'full' | 'partial' | 'last_digits' = 'partial', limit: number = 20, offset: number = 0) {
    return this.client.post('/search/', {
      query,
      search_type: searchType,
      limit,
      offset,
    });
  }

  async quickSearch(query: string, limit: number = 20) {
    return this.client.get('/search/quick', {
      params: { query, limit },
    });
  }

  async getSearchSuggestions(prefix: string, limit: number = 10) {
    return this.client.get('/search/suggestions', {
      params: { prefix, limit },
    });
  }

  async getSearchHistory(limit: number = 50) {
    return this.client.get('/search/history', {
      params: { limit },
    });
  }

  async getSimilarIMEIs(imeiId: string) {
    return this.client.get(`/search/similar/${imeiId}`);
  }

  async validateIMEI(imei: string) {
    return this.client.post('/search/validate', { imei });
  }

  async correctIMEI(imeiId: string, correctedValue: string) {
    return this.client.post(`/search/imei/${imeiId}/correct`, {}, {
      params: { corrected_value: correctedValue },
    });
  }

  // Dashboard
  async getDashboard() {
    return this.client.get('/dashboard');
  }

  async getStats() {
    return this.client.get('/dashboard/stats');
  }

  async getActivity(days: number = 7) {
    return this.client.get('/dashboard/activity', {
      params: { days },
    });
  }

  async getStatsByDevice() {
    return this.client.get('/dashboard/stats-by-device');
  }

  // Health
  async healthCheck() {
    return this.client.get('/health');
  }
}

export const apiClient = new APIClient();
