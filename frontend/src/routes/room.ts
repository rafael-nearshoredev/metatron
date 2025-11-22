import {
  Room,
  RoomEvent,
  RemoteTrack,
  RemoteTrackPublication,
  RemoteParticipant,
  LocalTrackPublication,
  LocalParticipant,
  Participant,
  Track,
  VideoPresets,
} from 'livekit-client'
import { roomApi } from '../utils/api-requests'

/**
 * LiveKit Room Manager
 * Handles connection, events, and media tracks.
 */
export class RoomManager {
  private room: Room | null = null
  private wsURL: string
  private container?: HTMLElement
  private roomName: string
  private participantName: string

  constructor(wsURL: string, roomName: string, participantName: string, container?: HTMLElement) {
    this.wsURL = wsURL
    this.roomName = roomName
    this.participantName = participantName
    this.container = container
  }

  /**
   * Connect to the LiveKit room.
   */
  async connect(): Promise<Room> {
    // Fetch token from backend
    console.log('🔑 Fetching access token from backend...')
    const tokenResponse = await roomApi.getAccessToken(this.roomName, this.participantName)
    const token = tokenResponse.token
    console.log('✅ Token received')

    this.room = new Room({
      adaptiveStream: true,
      dynacast: true,
      videoCaptureDefaults: {
        resolution: VideoPresets.h720.resolution,
      },
    })

    // Pre-warm connection for faster join
    await this.room.prepareConnection(this.wsURL, token)

    // Attach event listeners
    this.addEventListeners()

    // Connect to room
    await this.room.connect(this.wsURL, token)
    console.log('✅ Connected to room:', this.room.name)

    // Enable local camera & mic
    await this.room.localParticipant.enableCameraAndMicrophone()
    console.log('🎥 Local camera & mic enabled')

    return this.room
  }

  /**
   * Attach LiveKit event handlers.
   */
  private addEventListeners() {
    if (!this.room) return

    this.room
      .on(RoomEvent.TrackSubscribed, this.handleTrackSubscribed.bind(this))
      .on(RoomEvent.TrackUnsubscribed, this.handleTrackUnsubscribed.bind(this))
      .on(RoomEvent.ActiveSpeakersChanged, this.handleActiveSpeakersChanged.bind(this))
      .on(RoomEvent.ParticipantConnected, (p) =>
        console.log('👋 Participant connected:', p.identity)
      )
      .on(RoomEvent.ParticipantDisconnected, (p) =>
        console.log('👋 Participant disconnected:', p.identity)
      )
      .on(RoomEvent.Disconnected, this.handleDisconnect.bind(this))
      .on(RoomEvent.LocalTrackUnpublished, this.handleLocalTrackUnpublished.bind(this))
  }

  /**
   * Handle new remote track subscription.
   */
  private handleTrackSubscribed(
    track: RemoteTrack,
    _publication: RemoteTrackPublication,
    participant: RemoteParticipant
  ) {
    console.log(`📡 Track subscribed: ${track.kind} from ${participant.identity}`)
    if (track.kind === Track.Kind.Video || track.kind === Track.Kind.Audio) {
      const element = track.attach()
      element.autoplay = true
      if ('playsInline' in element) {
        (element as HTMLVideoElement).playsInline = true
      }
      element.className = `remote-${track.kind}`
      this.container?.appendChild(element)
    }
  }

  /**
   * Handle track unsubscription (cleanup).
   */
  private handleTrackUnsubscribed(
    track: RemoteTrack,
    _publication: RemoteTrackPublication,
    participant: RemoteParticipant
  ) {
    console.log(`🛑 Track unsubscribed: ${track.kind} from ${participant.identity}`)
    track.detach().forEach((el) => el.remove())
  }

  /**
   * Handle local track unpublishing.
   */
  private handleLocalTrackUnpublished(
    publication: LocalTrackPublication,
    _participant: LocalParticipant
  ) {
    console.log('🧹 Local track unpublished:', publication.track?.kind)
    publication.track?.detach().forEach((el) => el.remove())
  }

  /**
   * Active speaker change event.
   */
  private handleActiveSpeakersChanged(speakers: Participant[]) {
    console.log('🔊 Active speakers:', speakers.map((s) => s.identity))
  }

  /**
   * Handle disconnection event.
   */
  private handleDisconnect() {
    console.log('🔌 Disconnected from room')
  }

  /**
   * Disconnect and clean up.
   */
  disconnect(): void {
    if (this.room) {
      console.log('👋 Leaving room')
      this.room.disconnect()
      this.room = null
    }
  }

  /**
   * Get current room instance.
   */
  getRoom(): Room | null {
    return this.room
  }

  /**
   * Attach local video to a <video> element.
   */
  attachLocalVideo(videoElement: HTMLVideoElement): void {
    if (!this.room) return
    const localVideoTrack = Array.from(this.room.localParticipant.videoTrackPublications.values())[0]?.track
    if (localVideoTrack && videoElement) {
      localVideoTrack.attach(videoElement)
    }
  }

  /**
   * Get list of remote participants.
   */
  getRemoteParticipants(): RemoteParticipant[] {
    if (!this.room) return []
    return Array.from(this.room.remoteParticipants.values())
  }
}
/**
 * Simple function to connect to a room and return the room instance
 * Used by components for basic connection with dynamic token fetched from backend
 */
export async function connectToLiveKitRoom(wsURL: string, roomName: string, participantName: string): Promise<Room> {
  // Fetch token from backend
  console.log('🔑 Fetching access token from backend...')
  const tokenResponse = await roomApi.getAccessToken(roomName, participantName)
  const token = tokenResponse.token
  console.log('✅ Token received')

  const room = new Room()
  
  // Connect to the room
  await room.connect(wsURL, token)
  console.log('Connected to room:', room.name)
  
  // Enable camera and microphone
  await room.localParticipant.enableCameraAndMicrophone()
  console.log('Camera and microphone enabled')
  
  return room
}

/**
 * Attach a track to a video element
 */
export function attachTrackToElement(track: any, container: HTMLElement): void {
  if (track.kind === 'video') {
    const videoElement = document.createElement('video')
    videoElement.autoplay = true
    videoElement.playsInline = true
    videoElement.muted = false
    videoElement.className = 'remote-video'
    
    track.attach(videoElement)
    
    if (container) {
      container.appendChild(videoElement)
    }
  }
}
