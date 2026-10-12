import { defineRailway, project, service } from "railway/iac";

// solo-integrations: read-only metadata API for solo-web. Variables stay unmanaged (secrets live in Railway only).
// The service sleeps when idle (Railway Serverless). Build and healthcheck come from railway.toml.
// Needs the SDK to run: npm install railway (kept out of this Python repo; run it from a scratch directory).
// Region is not in the IaC; after the first deploy: railway scale --service solo-integrations asia-southeast1-eqsg3a=1 us-east4-eqdc4a=0
export default defineRailway(() => {
  const api = service("solo-integrations", {
    deploy: { sleepApplication: true },
  });

  return project("solo-integrations", {
    variables: { managed: false },
    resources: [api],
  });
});
