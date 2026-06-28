<template>
  <svg
    xmlns="http://www.w3.org/2000/svg"
    :width="size"
    :height="size"
    viewBox="0 0 24 24"
    fill="none"
    :stroke="color"
    stroke-width="1.8"
    stroke-linecap="round"
    stroke-linejoin="round"
  >
    <!-- Server chassis -->
    <rect x="2" y="2" width="20" height="20" rx="2" ry="2" />
    <!-- Slot lines -->
    <line x1="6" y1="8" x2="18" y2="8" />
    <line x1="6" y1="12" x2="18" y2="12" />
    <line x1="6" y1="16" x2="18" y2="16" />
    <!-- LED dots -->
    <circle cx="6" cy="6" r="1" fill="currentColor" stroke="none" />
  </svg>
</template>

<script setup lang="ts">
withDefaults(defineProps<{
  size?: number
  color?: string
}>(), {
  size: 24,
  color: 'currentColor',
})
</script>
