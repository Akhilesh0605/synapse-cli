"""Process and sandbox availability checks."""
import json
import subprocess


class ProcessMonitor:
	"""Helpers for checking sandbox readiness."""

	SANDBOX_IMAGE = "synapsecli-sandbox:latest"

	@staticmethod
	def is_docker_available() -> bool:
		try:
			result = subprocess.run(
				["docker", "--version"],
				capture_output=True,
				text=True,
				timeout=10,
			)
			return result.returncode == 0
		except (FileNotFoundError, subprocess.SubprocessError):
			return False

	@staticmethod
	def is_sandbox_image_built() -> bool:
		try:
			result = subprocess.run(
				["docker", "image", "inspect", ProcessMonitor.SANDBOX_IMAGE],
				capture_output=True,
				text=True,
				timeout=15,
			)
			return result.returncode == 0
		except (FileNotFoundError, subprocess.SubprocessError):
			return False

	@staticmethod
	def get_sandbox_status() -> dict:
		docker_available = ProcessMonitor.is_docker_available()
		image_built = False
		image_size_mb = None

		if docker_available:
			try:
				result = subprocess.run(
					["docker", "image", "inspect", ProcessMonitor.SANDBOX_IMAGE],
					capture_output=True,
					text=True,
					timeout=15,
				)
				if result.returncode == 0 and result.stdout.strip():
					image_built = True
					payload = json.loads(result.stdout)
					if payload and isinstance(payload, list):
						size_bytes = payload[0].get("Size")
						if isinstance(size_bytes, (int, float)):
							image_size_mb = round(size_bytes / (1024 * 1024), 2)
			except (FileNotFoundError, subprocess.SubprocessError, json.JSONDecodeError, IndexError, KeyError, TypeError):
				image_built = False

		return {
			"docker_available": docker_available,
			"image_built": image_built,
			"image_size_mb": image_size_mb,
			"ready": docker_available and image_built,
		}
