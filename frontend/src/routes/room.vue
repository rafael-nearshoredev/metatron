<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, shallowRef } from 'vue'
import { useRoute } from 'vue-router'
import { RoomManager, attachTrackToElement } from './room'
import type { RemoteParticipant } from 'livekit-client'

// Get the route to access the room ID parameter
const route = useRoute()
const roomId = computed(() => route.params.id as string || 'unknown')
const participantName = computed(() => route.query.name as string || 'Anonymous')

// Room state - use shallowRef to avoid deep reactivity on complex objects
const roomManager = shallowRef<RoomManager | null>(null)
const isConnected = ref<boolean>(false)
const participants = ref<RemoteParticipant[]>([])
const localVideoElement = ref<HTMLVideoElement | null>(null)
const remoteVideosContainer = ref<HTMLElement | null>(null)
const connectionError = ref<string>('')

// LiveKit configuration
const wsURL = import.meta.env.VITE_LIVEKIT_URL

onMounted(async () => {
  // Check if we have required parameters
  if (!roomId.value || !participantName.value) {
    connectionError.value = 'Missing room ID or participant name. Please go back and join again.'
    return
  }

  try {
    roomManager.value = new RoomManager(wsURL, roomId.value, participantName.value, remoteVideosContainer.value || undefined)
    
    // Connect to room
    const room = await roomManager.value.connect()
    console.log('Connected to room:', room.name)
    isConnected.value = true
    
    // Set up event listeners
    room.on('participantConnected', (participant) => {
      console.log('Participant connected:', participant.identity)
      updateParticipants()
    })
    
    room.on('participantDisconnected', (participant) => {
      console.log('Participant disconnected:', participant.identity)
      updateParticipants()
    })
    
    room.on('trackSubscribed', (track, _publication, participant) => {
      console.log('Track subscribed:', track.kind, participant.identity)
      if (remoteVideosContainer.value) {
        attachTrackToElement(track, remoteVideosContainer.value)
      }
    })
    
    // Attach local video
    if (localVideoElement.value) {
      roomManager.value.attachLocalVideo(localVideoElement.value)
    }
    
    updateParticipants()
    
  } catch (error) {
    console.error('Failed to connect to room:', error)
    connectionError.value = `Failed to connect: ${error instanceof Error ? error.message : 'Unknown error'}`
  }
})

onUnmounted(() => {
  if (roomManager.value) {
    roomManager.value.disconnect()
  }
})

function updateParticipants() {
  if (roomManager.value) {
    participants.value = roomManager.value.getRemoteParticipants()
  }
}
</script>

<template>
  <div class="room-container">
    <div class="room-header">
      <h1>Room {{ roomId }}</h1>
      <p class="participant-info">Welcome, {{ participantName }}!</p>
      <p class="room-status">
        <span v-if="connectionError" class="status-error">● {{ connectionError }}</span>
        <span v-else-if="isConnected" class="status-connected">● Connected</span>
        <span v-else class="status-connecting">● Connecting...</span>
      </p>
    </div>
    
    <div class="video-container">
      <!-- Local video -->
      <div class="local-video-wrapper">
        <video
          ref="localVideoElement"
          class="local-video"
          autoplay
          muted
          playsinline
        ></video>
        <div class="video-label">You</div>
      </div>
      
      <!-- Remote videos -->
      <div ref="remoteVideosContainer" class="remote-videos">
        <!-- Remote participant videos will be dynamically added here -->
      </div>
    </div>
    
    <div class="room-info">
      <p>Participants: {{ participants.length + 1 }}</p>
    </div>
    
    <div class="room-actions">
      <router-link to="/" class="back-btn">← Leave Room</router-link>
    </div>
  </div>
</template>

<style scoped>
.room-container {
  padding: 1rem;
  max-width: 1200px;
  margin: 0 auto;
  min-height: 100vh;
}

.room-header {
  text-align: center;
  margin-bottom: 2rem;
}

.room-header h1 {
  color: var(--color-primary);
  font-size: 2rem;
  margin-bottom: 0.5rem;
}

.room-status {
  font-size: 1rem;
  margin: 0;
}

.status-connected {
  color: #28a745;
}

.status-connecting {
  color: #ffc107;
}

.status-error {
  color: #dc3545;
}

.participant-info {
  font-size: 1rem;
  color: var(--color-text-secondary, #666);
  margin: 0.5rem 0;
}

.video-container {
  display: grid;
  grid-template-columns: 1fr 2fr;
  gap: 1rem;
  margin-bottom: 2rem;
  min-height: 400px;
}

.local-video-wrapper {
  position: relative;
  background: #000;
  border-radius: 0.5rem;
  overflow: hidden;
}

.local-video {
  width: 100%;
  height: 100%;
  object-fit: cover;
  min-height: 300px;
}

.video-label {
  position: absolute;
  bottom: 0.5rem;
  left: 0.5rem;
  background: rgba(0, 0, 0, 0.7);
  color: white;
  padding: 0.25rem 0.5rem;
  border-radius: 0.25rem;
  font-size: 0.8rem;
}

.remote-videos {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
  background: #f5f5f5;
  border-radius: 0.5rem;
  padding: 1rem;
  min-height: 300px;
}

.remote-videos:empty::after {
  content: "Waiting for other participants...";
  display: flex;
  align-items: center;
  justify-content: center;
  color: #666;
  font-style: italic;
  grid-column: 1 / -1;
}

:deep(.remote-video) {
  width: 100%;
  height: 200px;
  object-fit: cover;
  border-radius: 0.25rem;
  background: #000;
}

.room-info {
  text-align: center;
  margin-bottom: 1rem;
  color: var(--color-text-primary, #333);
}

.room-actions {
  text-align: center;
}

.back-btn {
  display: inline-block;
  padding: 0.75rem 1.5rem;
  background-color: #dc3545;
  color: var(--color-white);
  text-decoration: none;
  border-radius: 0.25rem;
  transition: background-color 0.3s ease;
  font-weight: 500;
}

.back-btn:hover {
  background-color: #c82333;
}

@media (max-width: 768px) {
  .video-container {
    grid-template-columns: 1fr;
  }
  
  .room-container {
    padding: 0.5rem;
  }
}
</style>