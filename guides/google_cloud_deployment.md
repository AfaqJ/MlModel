# Google Cloud Deployment Guide From Qatar

This is the fast beginner path for testing the MCT-37 FastAPI model service from Qatar.

## Quick Answer

- You **do need a Google Cloud billing account** attached to the project, even for Free Tier.
- You **do not need to upgrade to a paid billing account** if you still have an active Free Trial billing account.
- If Google asks for a card/payment method, that is normal for creating the billing account.
- For Qatar testing, use **Doha: `me-central1`**.
- Cloud Run’s free tier table includes **Doha (`me-central1`)**, Dammam (`me-central2`), and Tel Aviv (`me-west1`).
- Our **Dockerfile exists**, but the actual cloud container image is **not made yet**. You make it with `gcloud builds submit`.

## Direct Go-To Links

Use these links when you are in a hurry:

| What you need | Go here |
|---|---|
| Start Google Cloud Free Trial | https://console.cloud.google.com/freetrial |
| Open Google Cloud Console | https://console.cloud.google.com/ |
| Select or create a project | https://console.cloud.google.com/projectselector2/home/dashboard |
| Open Cloud Shell | https://console.cloud.google.com/cloudshell/editor |
| Enable APIs page | https://console.cloud.google.com/apis/library |
| Artifact Registry page | https://console.cloud.google.com/artifacts |
| Cloud Build history | https://console.cloud.google.com/cloud-build/builds |
| Cloud Run services | https://console.cloud.google.com/run |
| Billing overview | https://console.cloud.google.com/billing |
| Budgets and alerts | https://console.cloud.google.com/billing/budgets |
| Official Cloud Run pricing | https://cloud.google.com/run/pricing |
| Official Free Tier / Free Trial docs | https://docs.cloud.google.com/free/docs/free-cloud-features |

Think of it like this:

- `Dockerfile` = recipe.
- Docker image = cooked meal.
- Artifact Registry = fridge where Google stores the cooked meal.
- Cloud Run = waiter that serves the meal as an API.

## Billing: What Is Mandatory?

Google says a billing account is required to access the Free Tier. So yes, your test project needs billing attached.

But there are two cases:

1. **Free Trial billing account**: good for testing. Google’s docs say the Free Trial account is not billed, and the $300 credit pays for eligible usage.
2. **Paid billing account**: used after you upgrade/activate paid billing. Then usage beyond free limits or credits can charge your card.

So for testing ASAP:

1. Create a Google Cloud project.
2. Attach your Free Trial billing account.
3. Do **not** click “Activate”/upgrade to paid unless Google requires it or you intentionally want paid billing.
4. Set a budget alert anyway.

Official facts:

- Google says the Free Trial gives a **$300 Welcome credit for 90 days**.
- Google says **you are not billed during the Free Trial**.
- Google says signup can require a card/payment method to verify identity and reduce fraud.
- Google says **a billing account is required** to access the Google Cloud Free Tier.
- Google says Cloud Run Free Tier request-based billing includes **2 million requests/month**, **360,000 GB-seconds memory**, and **180,000 vCPU-seconds compute**.
- Google says Artifact Registry Free Tier includes **0.5 GB storage/month**. Our Docker image may be bigger than that, so set a budget alert.

## Free Tier In Qatar / Nearby

Use this region:

```bash
REGION="me-central1"
```

That is Doha, Qatar.

Nearby options:

- `me-central1` = Doha, Qatar. Best for you right now.
- `me-central2` = Dammam, Saudi Arabia.
- `me-west1` = Tel Aviv.
- `asia-south1` = Mumbai, also listed in Cloud Run free tier table, but farther.

For the company’s real deployment later, choose based on where the users/data are. For your current test, use Doha.

## Is The Container Image Already Made?

No. The project has the recipe, not the built cloud image.

We already have:

- `Dockerfile`
- `app/`
- `requirements.txt`
- `artifacts/v1.0.0/`

That is enough to build the image.

You still need to run:

```bash
gcloud builds submit --region="$REGION" --tag "$IMAGE"
```

That command builds the image in Google Cloud and pushes it to Artifact Registry.

## Step 1: Open Google Cloud Shell

Use Cloud Shell in the Google Cloud Console. It is easier than setting up your laptop.

In the console:

1. Go to project selector: https://console.cloud.google.com/projectselector2/home/dashboard
2. Select your test project.
3. Open Cloud Shell: https://console.cloud.google.com/cloudshell/editor
4. Upload or clone this project folder into Cloud Shell.
5. `cd` into the project folder, the one containing `Dockerfile`.

If you prefer your own terminal instead of Cloud Shell, install Google Cloud CLI:

https://docs.cloud.google.com/sdk/docs/install

## Step 2: Set Variables

Replace `your-project-id` with your real Google Cloud project ID.

```bash
PROJECT_ID="your-project-id"
REGION="me-central1"
REPO="mct37-docker"
SERVICE="mct37-invoice-classifier"
IMAGE="$REGION-docker.pkg.dev/$PROJECT_ID/$REPO/$SERVICE:v1.0.0"

gcloud config set project "$PROJECT_ID"
```

## Step 3: Enable Required Google APIs

Console page:

https://console.cloud.google.com/apis/library

```bash
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com
```

These mean:

- Cloud Run runs the API.
- Artifact Registry stores the image.
- Cloud Build builds the image.

## Step 4: Create Artifact Registry Repo

Console page:

https://console.cloud.google.com/artifacts

```bash
gcloud artifacts repositories create "$REPO" \
  --repository-format=docker \
  --location="$REGION" \
  --description="MCT-37 Docker images"
```

If it says the repo already exists, that is fine. Continue.

## Step 5: Build And Push The Image

Console page to watch builds:

https://console.cloud.google.com/cloud-build/builds

Run this from the folder that contains `Dockerfile`:

```bash
gcloud builds submit --region="$REGION" --tag "$IMAGE"
```

This can take a few minutes because it installs Python packages and copies the model artifact into the image.

## Step 6: Deploy To Cloud Run

Console page:

https://console.cloud.google.com/run

For easiest testing, deploy public first:

```bash
gcloud run deploy "$SERVICE" \
  --image "$IMAGE" \
  --region "$REGION" \
  --memory 2Gi \
  --cpu 1 \
  --concurrency 4 \
  --timeout 300 \
  --min-instances 0 \
  --allow-unauthenticated
```

This gives you a public URL. Use this only for quick testing. Do not send private invoice data to a public endpoint.

For safer private testing, use this instead:

```bash
gcloud run deploy "$SERVICE" \
  --image "$IMAGE" \
  --region "$REGION" \
  --memory 2Gi \
  --cpu 1 \
  --concurrency 4 \
  --timeout 300 \
  --min-instances 0 \
  --no-allow-unauthenticated
```

Private is better, but calling it needs an identity token.

## Step 7: Test It

Cloud Run prints a service URL. Save it:

```bash
SERVICE_URL="https://paste-your-cloud-run-url-here"
```

If public:

```bash
curl "$SERVICE_URL/health"
```

If private:

```bash
TOKEN="$(gcloud auth print-identity-token)"
curl -H "Authorization: Bearer $TOKEN" "$SERVICE_URL/health"
```

Prediction test:

```bash
curl -X POST "$SERVICE_URL/predict" \
  -H "Content-Type: application/json" \
  -d '{"item_text":"VACUNA CLOSTRIBAC 8 GOLD X 50 DOS.","provider":"COOPRINSEM"}'
```

Expected result: top prediction should be `EXP-2.3` / `Vacunas`.

## Cost Safety For Testing

Do these:

- Keep `--min-instances 0`.
- Do not run load tests.
- Delete old images if you build many versions.
- Set a budget alert in Billing: https://console.cloud.google.com/billing/budgets
- After testing, you can delete the service:

```bash
gcloud run services delete "$SERVICE" --region "$REGION"
```

Artifact Registry has a small free storage tier, but our final Docker image may be bigger than that because it includes Python dependencies and the model. If there is a charge, it should be small for short testing, but use billing alerts.

## Fastest Safe Recommendation

For you in Qatar right now:

```bash
REGION="me-central1"
```

Deploy with:

```bash
--min-instances 0
```

Use public only if you are testing with dummy text. Use private if testing real invoice lines.

## Later Company Deployment

When the company account is ready:

1. Repeat the same deployment in the company Google Cloud project.
2. Use private Cloud Run: `--no-allow-unauthenticated`.
3. Let the Vercel/Next.js backend call Cloud Run using Google OIDC.
4. Browser users should not call Cloud Run directly.

## Official Sources Checked

- Google Cloud Free Trial and Free Tier: https://docs.cloud.google.com/free/docs/free-cloud-features
  - Free Trial gives $300 Welcome credit over 90 days.
  - Google says you are not billed during the Free Trial.
  - Payment method can be required for signup verification.
  - A billing account is required for Free Tier.
  - Cloud Run Free Tier request-based limits are listed here.
  - Artifact Registry Free Tier storage is listed here.
- Cloud Run pricing/free tier regions: https://cloud.google.com/run/pricing
  - Cloud Run pricing depends on selected region.
  - The free tier is applied as a spending-based discount using Tier 1 pricing.
  - `me-central1` Doha is listed in the Cloud Run free tier region table.
- Cloud Run deploy command: https://docs.cloud.google.com/run/docs/deploying
  - Official deploy shape: `gcloud run deploy SERVICE --image IMAGE_URL`.
- Artifact Registry Docker repo quickstart: https://docs.cloud.google.com/artifact-registry/docs/docker/store-docker-container-images
  - Official Docker repository command uses `gcloud artifacts repositories create ... --repository-format=docker`.
- Artifact Registry pricing: https://cloud.google.com/artifact-registry/pricing
  - First 0.5 GB-month storage is free.
  - Co-locating repository and runtime region helps avoid cross-region transfer costs.
- Cloud Build image build/push: https://docs.cloud.google.com/build/docs/build-push-docker-image
  - Official Dockerfile build command uses `gcloud builds submit --tag ...`.
- Cloud Billing budget alerts: https://docs.cloud.google.com/billing/docs/how-to/budgets
  - Use Budgets & alerts to monitor costs for a project.
- Google Cloud CLI install: https://docs.cloud.google.com/sdk/docs/install
  - Use this only if you do not use Cloud Shell.
- Cloud Run service-to-service auth: https://docs.cloud.google.com/run/docs/authenticating/service-to-service
  - Use later for private Vercel/Next.js to Cloud Run calls.
