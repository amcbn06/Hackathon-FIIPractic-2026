import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The backend URL is read at build/runtime from VITE_API_URL (see .env).
// In dev we proxy /api to the FastAPI server so there are no CORS surprises.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: process.env.VITE_API_URL || "http://localhost:8000",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
    },
  },
});
