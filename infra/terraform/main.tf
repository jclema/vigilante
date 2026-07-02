terraform {
  required_version = ">= 1.6.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

resource "google_artifact_registry_repository" "vigilante" {
  location      = var.region
  repository_id = "vigilante"
  format        = "DOCKER"
}

resource "google_storage_bucket" "evidence" {
  name                        = "${var.project_id}-vigilante-evidence"
  location                    = var.region
  uniform_bucket_level_access = true

  lifecycle_rule {
    action {
      type = "Delete"
    }
    condition {
      age = 30
    }
  }
}

resource "google_pubsub_topic" "gbp_events" {
  name = "vigilante-gbp-events"
}

resource "google_cloud_run_v2_service" "app" {
  name     = "vigilante-app"
  location = var.region

  template {
    containers {
      image = var.container_image
      env {
        name  = "GOOGLE_CLOUD_PROJECT"
        value = var.project_id
      }
      env {
        name  = "GOOGLE_CLOUD_REGION"
        value = var.region
      }
    }
  }
}

resource "google_cloud_scheduler_job" "public_scan" {
  name     = "vigilante-public-scan"
  region   = var.region
  schedule = "0 * * * *"

  http_target {
    http_method = "POST"
    uri         = "${google_cloud_run_v2_service.app.uri}/api/scans/run"
    headers = {
      "Content-Type" = "application/json"
    }
    body = base64encode("{\"query\":\"yamaha medellin\"}")
  }
}

