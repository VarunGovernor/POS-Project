const path = require("path");

const root = path.resolve(__dirname, "../../..");

module.exports = {
  apps: [
    {
      name: "counteros-backend",
      cwd: root,
      script: "scripts/deploy/lightsail/start-backend.sh",
      autorestart: true,
      max_restarts: 10,
      out_file: "/var/log/counteros/backend.out.log",
      error_file: "/var/log/counteros/backend.err.log"
    },
    {
      name: "counteros-frontend",
      cwd: root,
      script: "scripts/deploy/lightsail/start-frontend.sh",
      autorestart: true,
      max_restarts: 10,
      out_file: "/var/log/counteros/frontend.out.log",
      error_file: "/var/log/counteros/frontend.err.log",
      env: {
        NEXT_PUBLIC_COUNTEROS_API_BASE_URL: "/api/v1"
      }
    }
  ]
};
