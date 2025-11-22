<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { roomApi } from '../utils/api-requests'

const router = useRouter()
const isConnecting = ref(false)
const connectionError = ref('')
const userName = ref('')

const roomName = 'Interview-001' // Default room name

async function joinInterview() {
  if (!userName.value.trim()) {
    connectionError.value = 'Please enter your name before joining.'
    return
  }

  isConnecting.value = true
  connectionError.value = ''
  
  try {
    // Get token from backend
    const tokenResponse = await roomApi.getAccessToken(roomName, userName.value)
    console.log('Token received from backend:', tokenResponse.token)

    // Navigate to room with the participant name and token
    router.push(`/room/${encodeURIComponent(roomName)}?name=${encodeURIComponent(userName.value)}&token=${encodeURIComponent(tokenResponse.token)}`)
    
  } catch (error) {
    console.error('Failed to get access token:', error)
    connectionError.value = `Failed to connect: ${error instanceof Error ? error.message : 'Unknown error'}`
  } finally {
    isConnecting.value = false
  }
}
</script>

<template>
  <div class="container">
    <h1>Welcome to Metatron Service!</h1>
    <p>Your interview will start soon! Please enter your name below:</p>

    <div class="interview-section">
      <input
        v-model="userName"
        type="text"
        placeholder="Enter your name"
        class="name-input"
      />

      <button
        @click="joinInterview"
        class="join-btn"
        :disabled="isConnecting"
      >
        <span v-if="isConnecting">Connecting...</span>
        <span v-else>Join Interview</span>
      </button>
      
      <div v-if="connectionError" class="error-message">
        {{ connectionError }}
      </div>
    </div>

    <p>
      Do you want to know more about us? Please visit
      <a href="#" target="_blank" rel="noopener">Metatron Service</a>
    </p>
  </div>
</template>

<style scoped>
.container {
  text-align: center;
  padding: 2rem;
}

.interview-section {
  margin-top: 2rem;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
}

.name-input {
  padding: 0.75rem 1rem;
  font-size: 1rem;
  border: 1px solid #ccc;
  border-radius: 0.5rem;
  width: 250px;
  max-width: 80%;
}

.join-btn {
  background-color: var(--color-primary);
  color: var(--color-white);
  border: none;
  padding: 0.75rem 1.5rem;
  font-size: 1rem;
  border-radius: 0.5rem;
  cursor: pointer;
  transition: background-color 0.3s ease;
  min-width: 150px;
}

.join-btn:hover:not(:disabled) {
  background-color: var(--color-primary-dark);
}

.join-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.error-message {
  margin-top: 0.5rem;
  padding: 0.75rem;
  background-color: #fee;
  color: #c33;
  border: 1px solid #fcc;
  border-radius: 0.25rem;
  font-size: 0.9rem;
}
</style>