import base64
import importlib.util
import io
import json
from pathlib import Path
import unittest
from unittest.mock import Mock, patch
from urllib.error import HTTPError, URLError
from urllib.request import Request

SCRIPT = Path(__file__).resolve().parents[1] / "skills/github-project-guide/scripts/github_data.py"
SPEC = importlib.util.spec_from_file_location("github_data", SCRIPT)
github = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(github)


def response(data=None, status="ok"):
    return {"status": status, "source_url": "https://api.github.com/evidence",
            "retrieved_at": "2026-10-10T00:00:00+00:00", "data": data}


def text_file(text, path="README.md"):
    return {"type": "file", "path": path, "sha": "blob-sha", "encoding": "base64",
            "html_url": "https://github.com/owner/repo/blob/commit/" + path,
            "content": base64.b64encode(text.encode()).decode()}


class FakeClient:
    def __init__(self, overrides=None):
        self.calls = []
        self.routes = {
            "/repos/owner/repo": response({"default_branch": "main", "private": False,
                                           "stargazers_count": 12, "open_issues_count": 2}),
            "/repos/owner/repo/commits": response([{"sha": "fixed-commit"}]),
            "/repos/owner/repo/readme": response(text_file("Project docs")),
            "/repos/owner/repo/contents": response([{"type": "file", "name": "LICENSE", "path": "LICENSE"}]),
            "/repos/owner/repo/contents/LICENSE": response(text_file("Custom license", "LICENSE")),
            "/repos/owner/repo/releases/latest": response({"tag_name": "v1", "body": "Notes", "assets": []}),
        }
        self.routes.update(overrides or {})

    def get(self, path, **params):
        self.calls.append((path, params))
        # Collection may normalize a response, so emulate fresh API objects.
        return json.loads(json.dumps(self.routes.get(path, response(status="not_found"))))


class RepositoryEvidenceTests(unittest.TestCase):
    def test_repository_urls_cannot_target_arbitrary_hosts_or_local_paths(self):
        self.assertEqual(github.parse_repository("https://github.com/isair/jarvis.git#readme"), "isair/jarvis")
        for value in ("https://github.com.evil.test/a/b", "https://token@github.com/a/b",
                      "http://github.com/a/b", "file:///tmp/repo", "a/../b", "a/b/issues/1"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                github.parse_repository(value)
        with self.assertRaises(ValueError):
            github.validate_doc_path("../outside.md")

    def test_content_reads_share_commit_and_never_invent_trend(self):
        client = FakeClient()
        result = github.collect_repo(client, "owner/repo")
        self.assertEqual(result["status"], "ok")
        self.assertTrue(result["snapshot"]["pinned"])
        for path, params in client.calls:
            if "/contents" in path or path.endswith("/readme"):
                self.assertEqual(params["ref"], "fixed-commit")
        self.assertEqual(result["trend"]["status"], "not_checked")
        self.assertNotIn("star_growth", result["metadata"]["data"])

    def test_unavailable_release_preserves_other_evidence(self):
        client = FakeClient({"/repos/owner/repo/releases/latest": response(status="rate_limited")})
        result = github.collect_repo(client, "owner/repo")
        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["readme"]["text"], "Project docs")
        self.assertEqual(result["latest_release"]["status"], "rate_limited")

    def test_no_license_is_not_reported_as_permission_to_use(self):
        result = github.collect_repo(FakeClient({"/repos/owner/repo/contents": response([])}), "owner/repo")
        self.assertEqual(result["license"]["status"], "not_found")
        self.assertIn("not a licensing conclusion", result["license"]["reason"])

    def test_missing_repo_stops_further_requests(self):
        client = FakeClient({"/repos/owner/repo": response(status="not_found")})
        self.assertEqual(github.collect_repo(client, "owner/repo")["status"], "error")
        self.assertEqual(len(client.calls), 1)

    def test_private_repository_is_not_read(self):
        client = FakeClient({"/repos/owner/repo": response({"private": True, "default_branch": "main"})})
        result = github.collect_repo(client, "owner/repo")
        self.assertEqual(result["status"], "error")
        self.assertEqual(len(client.calls), 1)

    def test_truncated_text_and_invalid_encoding_are_visible(self):
        item = github.document(response(text_file("中文说明")), "commit", 2)
        self.assertEqual(item["text"], "中文")
        self.assertTrue(item["truncated"])
        self.assertEqual(item["blob_sha"], "blob-sha")
        self.assertEqual(item["ref"], "commit")
        invalid = text_file("x")
        invalid["content"] = "!not base64!"
        self.assertEqual(github.document(response(invalid), "commit", 10)["status"], "unsupported")

    def test_issue_sample_excludes_pull_requests_and_describes_scope(self):
        items = [{"number": 1, "pull_request": {}, "body": "PR"},
                 {"number": 2, "body": "Bug", "html_url": "https://github.com/owner/repo/issues/2"}]
        client = FakeClient({"/repos/owner/repo/issues": response(items)})
        result = github.collect_repo(client, "owner/repo", include_issues=True)
        self.assertEqual([item["number"] for item in result["issues"]["items"]], [2])
        self.assertIn("not exhaustive", result["issues"]["scope"])

    def test_network_failure_and_rate_limit_do_not_expose_token(self):
        opener = Mock()
        opener.open.side_effect = URLError("secret-token")
        with patch.dict("os.environ", {"GITHUB_TOKEN": "secret-token"}):
            client = github.GitHubClient(use_token=True, opener=opener)
            result = client.get("/repos/owner/repo")
        self.assertEqual(result["status"], "network_error")
        self.assertNotIn("secret-token", json.dumps(result))
        opener.open.side_effect = HTTPError("https://api.github.com/", 403, "Forbidden",
                                           {"X-RateLimit-Remaining": "0"}, io.BytesIO())
        self.assertEqual(client.get("/repos/owner/repo")["status"], "rate_limited")

    def test_issue_body_truncation_marks_report_partial(self):
        client = FakeClient({"/repos/owner/repo/issues": response([{"number": 1, "body": "x" * 2001}])})
        result = github.collect_repo(client, "owner/repo", include_issues=True)
        self.assertTrue(result["issues"]["truncated"])
        self.assertEqual(result["status"], "partial")

    def test_release_truncation_marks_report_partial(self):
        client = FakeClient({"/repos/owner/repo/releases/latest": response({"body": "x" * 30000, "assets": []})})
        result = github.collect_repo(client, "owner/repo")
        self.assertTrue(result["latest_release"]["truncated"])
        self.assertEqual(result["status"], "partial")

    def test_redirect_cannot_forward_auth_to_another_host(self):
        handler = github.GitHubOnlyRedirect()
        with self.assertRaises(URLError):
            handler.redirect_request(Request("https://api.github.com/repos/a/b"), None, 302, "Found", {},
                                     "https://example.com/collect")


if __name__ == "__main__":
    unittest.main()
