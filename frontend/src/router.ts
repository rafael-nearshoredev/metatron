import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import Home from './components/Home.vue'
import Room from './routes/room.vue'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'Home',
    component: Home
  },
  {
    path: '/room/:id',
    name: 'Room',
    component: Room,
    props: true
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router