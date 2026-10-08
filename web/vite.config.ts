import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Saat dev, request /api diteruskan ke backend FastAPI (uvicorn di port 8000).
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { "/api": "http://localhost:8000" },
  },
});
