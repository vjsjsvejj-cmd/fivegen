export const IMAGE_MODELS = {
  "gpt-image-2": { name: "GPT Image 2", shortName: "GPT Image 2", resolutions: ["1K"], default_resolution: "1K", cost: 600, costType: "points" },
  "gpt-image-2-vip": { name: "GPT Image 2 VIP", shortName: "GPT Image 2 VIP", resolutions: ["1K", "2K", "4K"], default_resolution: "1K", cost: 1200, costType: "points" },
  "nano-banana-2": { name: "Nano Banana 2", shortName: "Nano Banana 2", resolutions: ["1K", "2K", "4K"], default_resolution: "1K", cost: 1200, costType: "points" },
  "nano-banana-2-cl": { name: "Nano Banana 2 CL", shortName: "Nano Banana 2 CL", resolutions: ["1K", "2K"], default_resolution: "1K", cost: 1600, costType: "points" },
  "nano-banana-2-4k-cl": { name: "Nano Banana 2 4K CL", shortName: "Nano Banana 2 4K CL", resolutions: ["4K"], default_resolution: "4K", cost: 3000, costType: "points" },
  "nano-banana-pro": { name: "Nano Banana Pro", shortName: "Nano Banana Pro", resolutions: ["1K", "2K", "4K"], default_resolution: "1K", cost: 1800, costType: "points" },
  "nano-banana-pro-cl": { name: "Nano Banana Pro CL", shortName: "Nano Banana Pro CL", resolutions: ["1K", "2K", "4K"], default_resolution: "1K", cost: 6000, costType: "points" },
  "nano-banana-pro-4k-vip": { name: "Nano Banana Pro 4K VIP", shortName: "Nano Banana Pro 4K VIP", resolutions: ["4K"], default_resolution: "4K", cost: 16000, costType: "points" },
  "seedream-5-0-lite": { name: "Seedream 5.0 Lite", shortName: "Seedream 5.0", resolutions: ["2K", "3K"], default_resolution: "2K", cost: 0.22, costType: "yuan" }
}

export const VIDEO_MODELS = {
  "seedance-2-0": {
    name: "Seedance 2.0",
    shortName: "Seedance 2.0",
    resolutions: ["480p", "720p", "1080p"],
    default_resolution: "720p",
    durations: ["4s", "5s", "6s", "7s", "8s", "9s", "10s", "11s", "12s", "13s", "14s", "15s"]
  }
}

export const IMAGE_ASPECT_RATIOS = ["auto", "16:9", "9:16", "1:1", "3:4", "4:3", "3:2", "2:3", "5:4", "4:5", "21:9"]
export const VIDEO_ASPECT_RATIOS = ["16:9", "9:16", "1:1", "3:4", "4:3", "21:9"]
export const FIVETV_ASPECT_RATIOS = ["auto", "16:9", "9:16", "1:1", "3:4", "4:3"]

export const VIDEO_RESOLUTION_CONFIG = {
  "480p": {
    "16:9": { width: 864, height: 496 },
    "4:3": { width: 752, height: 560 },
    "1:1": { width: 640, height: 640 },
    "3:4": { width: 560, height: 752 },
    "9:16": { width: 496, height: 864 },
    "auto": { width: 864, height: 496 },
    "21:9": { width: 992, height: 432 }
  },
  "720p": {
    "16:9": { width: 1280, height: 720 },
    "4:3": { width: 1112, height: 834 },
    "1:1": { width: 960, height: 960 },
    "3:4": { width: 834, height: 1112 },
    "9:16": { width: 720, height: 1280 },
    "auto": { width: 1280, height: 720 },
    "21:9": { width: 1470, height: 630 }
  },
  "1080p": {
    "16:9": { width: 1920, height: 1080 },
    "4:3": { width: 1664, height: 1248 },
    "1:1": { width: 1440, height: 1440 },
    "3:4": { width: 1248, height: 1664 },
    "9:16": { width: 1080, height: 1920 },
    "auto": { width: 1920, height: 1080 },
    "21:9": { width: 2206, height: 946 }
  }
}

export const FRAME_RATE = 24
