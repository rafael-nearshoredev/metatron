/**
 * API utilities for backend communication
 * Uses proxy configuration to mask the actual backend URL
 */

// API base path - uses proxy instead of direct backend URL
const API_BASE = '/api'

// Type definitions
export interface ApiResponse<T = any> {
  data?: T
  message?: string
  success?: boolean
}

export interface RoomData {
  name: string
  maxParticipants?: number
  settings?: {
    video?: boolean
    audio?: boolean
    recording?: boolean
  }
}

export interface Room {
  id: string
  name: string
  maxParticipants: number
  currentParticipants: number
  settings: {
    video: boolean
    audio: boolean
    recording: boolean
  }
  createdAt: string
}

export interface ParticipantData {
  participantName: string
  permissions?: {
    canPublish?: boolean
    canSubscribe?: boolean
  }
}

export interface JoinRoomResponse {
  participantId: string
  token: string
  room: Room
}

export interface TokenRequest {
  room_name: string
  participant_name: string
  metadata?: Record<string, any>
  voice_id?: string
}

export interface TokenResponse {
  room_name: string
  token: string
  url: string
}

export interface UserProfile {
  id: string
  displayName: string
  email?: string
  avatar?: string
  createdAt: string
  updatedAt: string
}

export interface HealthStatus {
  status: 'healthy' | 'unhealthy'
  timestamp: string
  version?: string
  uptime?: number
}

interface RequestOptions extends RequestInit {
  headers?: Record<string, string>
}

/**
 * HTTP client with common configuration
 */
class ApiClient {
  private baseURL: string

  constructor() {
    this.baseURL = API_BASE
  }

  /**
   * Make a fetch request with common configuration
   */
  async request<T = any>(endpoint: string, options: RequestOptions = {}): Promise<T> {
    const url = `${this.baseURL}${endpoint}`
    
    const config: RequestInit = {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    }

    // Add body serialization for non-GET requests
    if (config.body && typeof config.body === 'object') {
      config.body = JSON.stringify(config.body)
    }

    try {
      const response = await fetch(url, config)
      
      // Handle non-JSON responses
      const contentType = response.headers.get('content-type')
      let data: any
      
      if (contentType && contentType.includes('application/json')) {
        data = await response.json()
      } else {
        data = await response.text()
      }

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${data.message || data || 'Request failed'}`)
      }

      return data
    } catch (error) {
      console.error(`API request failed: ${endpoint}`, error)
      throw error
    }
  }

  /**
   * GET request
   */
  async get<T = any>(endpoint: string, params: Record<string, string> = {}): Promise<T> {
    const queryString = new URLSearchParams(params).toString()
    const url = queryString ? `${endpoint}?${queryString}` : endpoint
    
    return this.request<T>(url, {
      method: 'GET',
    })
  }

  /**
   * POST request
   */
  async post<T = any>(endpoint: string, data: any = {}): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'POST',
      body: data,
    })
  }

  /**
   * PUT request
   */
  async put<T = any>(endpoint: string, data: any = {}): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'PUT',
      body: data,
    })
  }

  /**
   * DELETE request
   */
  async delete<T = any>(endpoint: string): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'DELETE',
    })
  }
}

// Create singleton instance
const apiClient = new ApiClient()

/**
 * Room API endpoints
 */
export const roomApi = {
  /**
   * Create a new room
   */
  async createRoom(roomData: RoomData): Promise<Room> {
    return apiClient.post<Room>('/rooms', roomData)
  },

  /**
   * Get room information
   */
  async getRoom(roomId: string): Promise<Room> {
    return apiClient.get<Room>(`/rooms/${roomId}`)
  },

  /**
   * Join a room and get access token
   */
  async joinRoom(roomId: string, participantData: ParticipantData): Promise<JoinRoomResponse> {
    return apiClient.post<JoinRoomResponse>(`/rooms/${roomId}/join`, participantData)
  },

  /**
   * Leave a room
   */
  async leaveRoom(roomId: string, participantId: string): Promise<void> {
    return apiClient.post<void>(`/rooms/${roomId}/leave`, { participantId })
  },

  /**
   * Get room participants
   */
  async getRoomParticipants(roomId: string): Promise<UserProfile[]> {
    return apiClient.get<UserProfile[]>(`/rooms/${roomId}/participants`)
  },

  /**
   * Get access token for LiveKit
   */
  async getAccessToken(roomName: string, participantName: string, metadata?: Record<string, any>, voiceId?: string): Promise<TokenResponse> {
    return apiClient.post<TokenResponse>('/rooms/create', {
      room_name: roomName,
      participant_name: participantName,
      ...(metadata && { metadata }),
      ...(voiceId && { voice_id: voiceId }),
    })
  },
}

/**
 * User API endpoints
 */
export const userApi = {
  /**
   * Get user profile
   */
  async getProfile(userId: string): Promise<UserProfile> {
    return apiClient.get<UserProfile>(`/users/${userId}`)
  },

  /**
   * Update user profile
   */
  async updateProfile(userId: string, profileData: Partial<UserProfile>): Promise<UserProfile> {
    return apiClient.put<UserProfile>(`/users/${userId}`, profileData)
  },
}

/**
 * Health check endpoint
 */
export const healthApi = {
  /**
   * Check API health
   */
  async check(): Promise<HealthStatus> {
    return apiClient.get<HealthStatus>('/health')
  },
}

// Export the client for custom requests
export { apiClient }

// Default export
export default {
  roomApi,
  userApi,
  healthApi,
  apiClient,
}