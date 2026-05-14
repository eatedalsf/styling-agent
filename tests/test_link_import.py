"""
Tests for link_import.py — the Product Link import feature.

Network calls are stubbed so the suite stays deterministic and works
offline. Live retailer fetches are intentionally NOT tested here —
those would be flaky against rate-limited or bot-blocked sites.

Run with:
    python -m unittest tests.test_link_import
"""

import os
import sys
import unittest
from unittest import mock

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from link_import import (  # noqa: E402
    extract_store_from_url,
    slug_to_name,
    infer_fields_from_text,
    extract_metadata_from_html,
    fetch_url_metadata,
    import_product_link,
)
from wardrobe_tool import (  # noqa: E402
    save_user_item,
    get_user_wardrobe,
    get_wardrobe,
    USER_DATA_PATH,
)


# ─────────────────────────────────────────────
# URL / DOMAIN PARSING
# ─────────────────────────────────────────────

class TestStoreExtraction(unittest.TestCase):
    """Store names should be presentable (alias lookup for known retailers,
    capitalized fallback for unknowns) and tolerate every common subdomain
    pattern including numbered www variants like www2.hm.com."""

    def test_simple_www_dot_com_uses_alias(self):
        self.assertEqual(extract_store_from_url("https://www.zara.com/x"), "Zara")

    def test_bare_dot_com_uses_alias(self):
        self.assertEqual(extract_store_from_url("https://nordstrom.com/foo"), "Nordstrom")

    def test_country_subdomain(self):
        self.assertEqual(extract_store_from_url("https://uk.zara.com/x"), "Zara")

    def test_shop_subdomain(self):
        self.assertEqual(extract_store_from_url("https://shop.nordstrom.com/y"), "Nordstrom")

    def test_co_uk_tld(self):
        self.assertEqual(extract_store_from_url("https://www.zara.co.uk/y"), "Zara")

    def test_hm_www2_normalizes_to_brand_name(self):
        # The bug that prompted this pass: www2.hm.com used to yield "www2".
        self.assertEqual(extract_store_from_url("https://www2.hm.com/en_us/productpage.1351318001.html"), "H&M")

    def test_hm_with_country_and_www2(self):
        # Stacked subdomains should strip iteratively.
        self.assertEqual(extract_store_from_url("https://www2.us.hm.com/foo"), "H&M")

    def test_unknown_store_capitalized_fallback(self):
        self.assertEqual(extract_store_from_url("https://www.exampleshop.com/x"), "Exampleshop")

    def test_lululemon_alias_preserves_lowercase(self):
        # Some brand names are stylized — alias map respects that.
        self.assertEqual(extract_store_from_url("https://shop.lululemon.com/x"), "lululemon")

    def test_empty_string(self):
        self.assertEqual(extract_store_from_url(""), "")

    def test_malformed_returns_string(self):
        out = extract_store_from_url("not a url")
        self.assertIsInstance(out, str)


class TestSlugToName(unittest.TestCase):
    def test_basic_kebab_slug(self):
        self.assertEqual(
            slug_to_name("https://www.example.com/products/cream-linen-blazer"),
            "Cream Linen Blazer",
        )

    def test_slug_with_sku_suffix(self):
        # SKU numbers like 4-digit-plus runs should be stripped.
        name = slug_to_name("https://shop.example.com/midi-dress-burgundy-123456")
        self.assertIn("Midi Dress Burgundy", name)
        self.assertNotIn("123456", name)

    def test_html_extension_dropped(self):
        self.assertEqual(
            slug_to_name("https://x.com/shop/black-trench-coat.html"),
            "Black Trench Coat",
        )

    def test_pure_sku_path_returns_empty(self):
        # /p/123456789 is pure SKU — no real name to extract.
        self.assertEqual(slug_to_name("https://x.com/p/123456789"), "")

    def test_url_encoded_path(self):
        self.assertEqual(
            slug_to_name("https://x.com/shop/cream%20linen%20blazer"),
            "Cream Linen Blazer",
        )

    def test_skips_category_words(self):
        # Last segment is "products" — fallback to deeper meaningful segment.
        name = slug_to_name("https://x.com/women/dresses/midi-silk-dress/products")
        self.assertIn("Midi Silk Dress", name)

    def test_hm_productpage_slug_returns_empty(self):
        # The H&M-style slug consists only of noise + SKU. Cleaner to
        # return empty than to surface "Productpage." to the user.
        self.assertEqual(
            slug_to_name("https://www2.hm.com/en_us/productpage.1351318001.html"),
            "",
        )

    def test_pdp_noise_token_rejected(self):
        self.assertEqual(slug_to_name("https://x.com/shop/pdp/999999"), "")

    def test_orphan_punctuation_stripped(self):
        # After SKU strip the slug used to leave "productpage." — verify
        # punctuation no longer sneaks through to the displayed name.
        out = slug_to_name("https://x.com/p/cream-blazer.1234567")
        self.assertEqual(out, "Cream Blazer")
        self.assertNotIn(".", out)


class TestFieldInference(unittest.TestCase):
    def test_category_dress(self):
        out = infer_fields_from_text("midi silk dress")
        self.assertEqual(out["category"], "dress")

    def test_category_blazer_maps_to_outerwear(self):
        out = infer_fields_from_text("cream linen blazer for the office")
        self.assertEqual(out["category"], "outerwear")

    def test_category_jeans_maps_to_bottom(self):
        out = infer_fields_from_text("dark wash skinny jeans")
        self.assertEqual(out["category"], "bottom")

    def test_category_heels_maps_to_shoes(self):
        out = infer_fields_from_text("black pointed-toe heels")
        self.assertEqual(out["category"], "shoes")

    def test_category_tote_maps_to_accessory(self):
        out = infer_fields_from_text("tan leather tote bag")
        self.assertEqual(out["category"], "accessory")

    def test_color_navy(self):
        out = infer_fields_from_text("Navy Wool Suit")
        self.assertEqual(out["color"], "navy")

    def test_color_terracotta(self):
        out = infer_fields_from_text("terracotta silk blouse")
        self.assertEqual(out["color"], "terracotta")

    def test_tag_work(self):
        out = infer_fields_from_text("the perfect blazer for the office")
        self.assertIn("work", out["tags"])

    def test_tag_gym_athletic(self):
        out = infer_fields_from_text("athletic running tights")
        self.assertIn("gym", out["tags"])

    def test_tag_multiple(self):
        out = infer_fields_from_text("a versatile travel and work dress")
        self.assertIn("work", out["tags"])
        self.assertIn("travel", out["tags"])

    def test_no_matches_returns_empty_defaults(self):
        out = infer_fields_from_text("xyzzy 9999 qqqqq")
        self.assertIsNone(out["category"])
        self.assertIsNone(out["color"])
        self.assertEqual(out["tags"], [])


# ─────────────────────────────────────────────
# METADATA EXTRACTION (HTML → fields, no network)
# ─────────────────────────────────────────────

_FAKE_HTML = """\
<!DOCTYPE html>
<html>
<head>
    <title>Cream Linen Blazer — Example Brand</title>
    <meta property="og:title" content="Cream Linen Blazer">
    <meta property="og:image" content="https://cdn.example.com/blazer.jpg">
    <meta name="description" content="A tailored cream linen blazer perfect for work or dinner.">
</head>
<body>...</body>
</html>
"""


class TestHtmlMetadataExtraction(unittest.TestCase):
    def test_extracts_title(self):
        m = extract_metadata_from_html(_FAKE_HTML)
        self.assertEqual(m["title"], "Cream Linen Blazer — Example Brand")

    def test_extracts_og_title(self):
        m = extract_metadata_from_html(_FAKE_HTML)
        self.assertEqual(m["og_title"], "Cream Linen Blazer")

    def test_extracts_og_image(self):
        m = extract_metadata_from_html(_FAKE_HTML)
        self.assertEqual(m["og_image"], "https://cdn.example.com/blazer.jpg")

    def test_extracts_description(self):
        m = extract_metadata_from_html(_FAKE_HTML)
        self.assertIn("cream linen blazer", m["description"].lower())

    def test_attr_order_reversed(self):
        # content="..." before property="og:..."
        html = '<meta content="Reversed Order Title" property="og:title">'
        m = extract_metadata_from_html(html)
        self.assertEqual(m["og_title"], "Reversed Order Title")

    def test_missing_metadata_returns_nones(self):
        m = extract_metadata_from_html("<html><body>no head</body></html>")
        for k in ("title", "og_title", "og_image", "description"):
            self.assertIsNone(m[k], f"{k} should be None on a page without meta")


# ─────────────────────────────────────────────
# FETCH FALLBACK (no real network in tests)
# ─────────────────────────────────────────────

class TestFetchFallback(unittest.TestCase):
    """fetch_url_metadata must never raise. Patch urlopen to simulate failures."""

    def test_network_error_returns_clean_failure(self):
        import urllib.error
        with mock.patch("link_import.urllib.request.urlopen",
                        side_effect=urllib.error.URLError("Connection refused")):
            r = fetch_url_metadata("https://example.com/x")
            self.assertFalse(r["success"])
            self.assertIn("Network error", r["error"])

    def test_http_error_returns_clean_failure(self):
        import urllib.error
        with mock.patch(
            "link_import.urllib.request.urlopen",
            side_effect=urllib.error.HTTPError("u", 403, "Forbidden", {}, None),
        ):
            r = fetch_url_metadata("https://example.com/x")
            self.assertFalse(r["success"])
            self.assertIn("HTTP 403", r["error"])

    def test_unexpected_exception_returns_clean_failure(self):
        with mock.patch("link_import.urllib.request.urlopen",
                        side_effect=RuntimeError("something broke")):
            r = fetch_url_metadata("https://example.com/x")
            self.assertFalse(r["success"])
            self.assertIn("Could not read page", r["error"])


# ─────────────────────────────────────────────
# ORCHESTRATION: import_product_link
# ─────────────────────────────────────────────

class TestImportProductLink(unittest.TestCase):

    def test_offline_path_still_returns_url_inference(self):
        # Skip fetch entirely — pure URL inference.
        result = import_product_link(
            "https://www.exampleshop.com/women/work/cream-linen-blazer",
            fetch_metadata=False,
        )
        self.assertEqual(result["source_store"], "Exampleshop")
        self.assertIn("Cream Linen Blazer", result["inferred"]["name"])
        self.assertEqual(result["inferred"]["category"], "outerwear")
        self.assertEqual(result["inferred"]["color"], "cream")
        self.assertIn("work", result["inferred"]["tags"])
        self.assertFalse(result["fetched"])
        self.assertIsNone(result["source_image_url"])

    def test_hm_url_offline_yields_blank_name(self):
        # Real bug reproduction: H&M URL, no fetch — name should be empty
        # (not "Productpage.") and store should be "H&M".
        result = import_product_link(
            "https://www2.hm.com/en_us/productpage.1351318001.html",
            fetch_metadata=False,
        )
        self.assertEqual(result["source_store"], "H&M")
        self.assertEqual(result["inferred"]["name"], "")
        # Color should NOT be invented when no metadata is available.
        self.assertIsNone(result["inferred"]["color"])
        self.assertFalse(result["fetched"])

    def test_hm_url_after_timeout_still_blank_name(self):
        # Simulate the real failure: fetch times out / 403s. The orchestrator
        # should report fetched=False, store="H&M", name="", color=None.
        with mock.patch(
            "link_import.fetch_url_metadata",
            return_value={"success": False, "extracted": {}, "error": "Network error: timed out"},
        ):
            r = import_product_link("https://www2.hm.com/en_us/productpage.1351318001.html")
            self.assertFalse(r["fetched"])
            self.assertEqual(r["source_store"], "H&M")
            self.assertEqual(r["inferred"]["name"], "")
            self.assertIsNone(r["inferred"]["color"])
            self.assertIn("timed out", r["fetch_error"] or "")

    def test_with_fake_fetch_uses_og_title(self):
        # Patch fetch_url_metadata to return canned page metadata.
        canned = {
            "success": True,
            "extracted": {
                "title": "Original Title",
                "og_title": "Better OG Title",
                "og_image": "https://cdn.example.com/img.jpg",
                "description": "A navy work dress.",
            },
            "error": None,
        }
        with mock.patch("link_import.fetch_url_metadata", return_value=canned):
            r = import_product_link("https://shop.example.com/products/some-dress-9999")
            self.assertTrue(r["fetched"])
            self.assertEqual(r["inferred"]["name"], "Better OG Title")
            self.assertEqual(r["source_image_url"], "https://cdn.example.com/img.jpg")
            # Description text feeds inference too.
            self.assertEqual(r["inferred"]["color"], "navy")
            self.assertIn("work", r["inferred"]["tags"])

    def test_failed_fetch_still_yields_inference(self):
        with mock.patch(
            "link_import.fetch_url_metadata",
            return_value={"success": False, "extracted": {}, "error": "HTTP 403"},
        ):
            r = import_product_link("https://www.zara.com/women/midi-dress-black")
            self.assertFalse(r["fetched"])
            self.assertEqual(r["fetch_error"], "HTTP 403")
            self.assertEqual(r["source_store"], "Zara")
            self.assertEqual(r["inferred"]["category"], "dress")
            self.assertEqual(r["inferred"]["color"], "black")

    def test_empty_url_does_not_crash(self):
        r = import_product_link("")
        self.assertEqual(r["source_store"], "")
        self.assertEqual(r["inferred"]["name"], "")
        self.assertFalse(r["fetched"])


# ─────────────────────────────────────────────
# SAVE PATH: link-imported items reach the agent
# ─────────────────────────────────────────────

class TestLinkImportedItemReachesAgent(unittest.TestCase):
    """save_user_item with link_metadata writes source_* fields and the
    item appears in the merged wardrobe and the occasion filter pool."""

    @classmethod
    def setUpClass(cls):
        cls._original = None
        if os.path.exists(USER_DATA_PATH):
            with open(USER_DATA_PATH, "r", encoding="utf-8") as f:
                cls._original = f.read()

    @classmethod
    def tearDownClass(cls):
        if cls._original is not None:
            with open(USER_DATA_PATH, "w", encoding="utf-8") as f:
                f.write(cls._original)
        else:
            if os.path.exists(USER_DATA_PATH):
                os.remove(USER_DATA_PATH)

    def setUp(self):
        import json as _json
        with open(USER_DATA_PATH, "w", encoding="utf-8") as f:
            _json.dump({"clothing": [], "shoes": [], "accessories": []}, f)

    def test_link_metadata_persisted(self):
        r = save_user_item(
            category="outerwear",
            item_fields={
                "name": "Cream Linen Blazer",
                "color": "cream",
                "season": ["spring", "summer", "all"],
                "tags": ["work"],
            },
            link_metadata={
                "source_url":       "https://www.exampleshop.com/cream-blazer",
                "source_store":     "exampleshop",
                "source_image_url": "https://cdn.example.com/x.jpg",
            },
        )
        self.assertTrue(r.get("success"), msg=r.get("error"))
        item = r["item"]
        self.assertEqual(item["source_url"], "https://www.exampleshop.com/cream-blazer")
        self.assertEqual(item["source_store"], "exampleshop")
        self.assertEqual(item["source_image_url"], "https://cdn.example.com/x.jpg")

    def test_link_item_appears_in_merged_wardrobe(self):
        save_user_item(
            category="outerwear",
            item_fields={"name": "Link Test Blazer", "color": "cream",
                         "tags": ["work"], "season": ["all"]},
            link_metadata={"source_url": "https://x.com/y", "source_store": "x"},
        )
        merged = get_wardrobe()
        names = [i["name"] for i in merged["wardrobe"]["clothing"]]
        self.assertIn("Link Test Blazer", names)

    def test_link_item_eligible_for_occasion_pool(self):
        from wardrobe_tool import filter_items_by_occasion
        save_user_item(
            category="top",
            item_fields={"name": "Link Test Work Top", "color": "ivory",
                         "tags": ["work"], "season": ["fall", "spring", "all"]},
            link_metadata={"source_url": "https://x.com/y", "source_store": "x"},
        )
        pool = filter_items_by_occasion("work", "fall")
        names = [i["name"] for i in pool["clothing"]]
        self.assertIn("Link Test Work Top", names)

    def test_no_link_metadata_no_source_fields(self):
        # Backward-compat: items saved WITHOUT link_metadata don't get
        # source_url / source_store added.
        r = save_user_item(
            category="top",
            item_fields={"name": "Plain Top", "color": "white", "tags": ["casual"]},
        )
        self.assertTrue(r.get("success"))
        self.assertNotIn("source_url",   r["item"])
        self.assertNotIn("source_store", r["item"])


# ─────────────────────────────────────────────
# IMPROVED INFERENCE — provenance, image color, category fallbacks
# ─────────────────────────────────────────────

class TestImageColorInference(unittest.TestCase):
    """Image-based color inference is best-effort: it should map a
    near-white PIL-rendered tile to "white" / "ivory" / "cream", a
    near-black tile to "black", a navy tile to "navy", etc. The output
    feeds into the orchestrator only as a LAST-resort color signal —
    metadata and text always win."""

    def _make_solid_image_url_mock(self, rgb):
        """Return a mock that makes urlopen serve a 64x64 solid-RGB JPEG.
        Used to stub the HTTP fetch inside infer_color_from_image_url."""
        from PIL import Image
        import io
        buf = io.BytesIO()
        Image.new("RGB", (64, 64), rgb).save(buf, format="PNG")
        raw_bytes = buf.getvalue()

        class _FakeResp:
            def __init__(self, b): self._b = b
            def __enter__(self): return self
            def __exit__(self, *a): return False
            def read(self, *a, **k): return self._b
        return _FakeResp(raw_bytes)

    def test_white_image_maps_to_white_family(self):
        from link_import import infer_color_from_image_url
        with mock.patch("urllib.request.urlopen",
                        return_value=self._make_solid_image_url_mock(
                            (245, 240, 233))):
            color, conf = infer_color_from_image_url("https://x/x.jpg")
        self.assertIn(color, ("white", "ivory", "cream"))
        self.assertIn(conf, ("high", "medium"))

    def test_navy_image_maps_to_navy(self):
        from link_import import infer_color_from_image_url
        with mock.patch("urllib.request.urlopen",
                        return_value=self._make_solid_image_url_mock(
                            (30, 40, 65))):
            color, conf = infer_color_from_image_url("https://x/x.jpg")
        self.assertIn(color, ("navy", "charcoal", "black"))

    def test_black_image_maps_to_black(self):
        from link_import import infer_color_from_image_url
        with mock.patch("urllib.request.urlopen",
                        return_value=self._make_solid_image_url_mock(
                            (20, 18, 16))):
            color, conf = infer_color_from_image_url("https://x/x.jpg")
        self.assertIn(color, ("black", "charcoal"))

    def test_network_failure_returns_empty(self):
        from link_import import infer_color_from_image_url
        with mock.patch("urllib.request.urlopen",
                        side_effect=Exception("network down")):
            color, conf = infer_color_from_image_url("https://x/x.jpg")
        self.assertEqual(color, "")
        self.assertEqual(conf, "low")


class TestProvenanceTracking(unittest.TestCase):
    """Each inferred field carries a source label so the UI can render
    'from metadata' / 'from image' captions next to the chip."""

    def _canned(self, **kw):
        """Build a minimal extracted-metadata dict for fetch_url_metadata."""
        base = {"title": None, "og_title": None, "og_image": None,
                "og_description": None, "description": None,
                "jsonld_product": {}}
        base.update(kw)
        return {"success": True, "extracted": base, "error": None}

    def test_jsonld_color_marked_as_metadata(self):
        canned = self._canned(jsonld_product={"name": "Crew Tee",
                                                "color": "white",
                                                "category": "Tops"})
        with mock.patch("link_import.fetch_url_metadata",
                        return_value=canned):
            r = import_product_link("https://www.uniqlo.com/us/en/products/X")
        self.assertEqual(r["inferred"]["color"], "white")
        self.assertEqual(r["sources"]["color"], "metadata")

    def test_metadata_color_wins_over_image(self):
        """When JSON-LD provides a color, the image sampler must NOT
        be consulted — the metadata value is canonical."""
        canned = self._canned(
            jsonld_product={"name": "Crew Tee", "color": "navy",
                            "image": "https://x/img.png"},
        )
        with mock.patch("link_import.fetch_url_metadata",
                        return_value=canned), \
             mock.patch("link_import.infer_color_from_image_url",
                        return_value=("red", "high")) as image_mock:
            r = import_product_link("https://uniqlo.com/p")
        # Color is navy (metadata), not red (would-be image guess)
        self.assertEqual(r["inferred"]["color"], "navy")
        self.assertEqual(r["sources"]["color"], "metadata")
        image_mock.assert_not_called()

    def test_text_color_wins_over_image(self):
        canned = self._canned(
            og_title="Ivory Silk Blouse",
            og_image="https://x/img.png",
        )
        with mock.patch("link_import.fetch_url_metadata",
                        return_value=canned), \
             mock.patch("link_import.infer_color_from_image_url",
                        return_value=("red", "high")) as image_mock:
            r = import_product_link("https://retailer.com/p")
        self.assertEqual(r["inferred"]["color"], "ivory")
        self.assertEqual(r["sources"]["color"], "text")
        image_mock.assert_not_called()

    def test_image_color_used_only_when_metadata_and_text_are_silent(self):
        canned = self._canned(
            og_title="Women's Mini T-Shirt",  # no color words
            og_image="https://x/img.png",
        )
        with mock.patch("link_import.fetch_url_metadata",
                        return_value=canned), \
             mock.patch("link_import.infer_color_from_image_url",
                        return_value=("white", "high")):
            r = import_product_link("https://uniqlo.com/p")
        self.assertEqual(r["inferred"]["color"], "white")
        self.assertEqual(r["sources"]["color"], "image:high")

    def test_low_confidence_image_color_dropped(self):
        canned = self._canned(og_title="Cool tee", og_image="https://x/i.png")
        with mock.patch("link_import.fetch_url_metadata",
                        return_value=canned), \
             mock.patch("link_import.infer_color_from_image_url",
                        return_value=("brown", "low")):
            r = import_product_link("https://r.com/p")
        self.assertIsNone(r["inferred"]["color"])


class TestUniqloWhiteTeeScenario(unittest.TestCase):
    """Integration: the user's reported Uniqlo white T-shirt URL should
    yield a usable set of inferred fields without manual entry."""

    def test_uniqlo_white_tee_full_inference(self):
        # Simulate the Uniqlo page that returns og:title naming the
        # product but NO color metadata, AND the image is white.
        canned = {
            "success": True,
            "extracted": {
                "title": "Womens Mini T-Shirt | UNIQLO US",
                "og_title": "Womens Mini T-Shirt | UNIQLO US",
                "og_image": "https://image.uniqlo.com/x.png",
                "og_description": "Cotton crew-neck tee",
                "description": "Cotton crew-neck tee",
                "jsonld_product": {},
            },
            "error": None,
        }
        with mock.patch("link_import.fetch_url_metadata",
                        return_value=canned), \
             mock.patch("link_import.infer_color_from_image_url",
                        return_value=("white", "high")):
            r = import_product_link(
                "https://www.uniqlo.com/us/en/products/E422992-000")
        inf = r["inferred"]
        # Store-suffix stripped from name.
        self.assertNotIn("UNIQLO", inf["name"])
        self.assertIn("T-Shirt", inf["name"])
        # Color inferred from the image (since neither metadata nor
        # text named one).
        self.assertEqual(inf["color"], "white")
        self.assertEqual(r["sources"]["color"], "image:high")
        # Category from text — "Tee" / "T-shirt" → top.
        self.assertEqual(inf["category"], "top")
        # Formality — casual (tee).
        self.assertEqual(inf["formality"], "casual")
        # Season expanded — NOT just ["all"] for a t-shirt.
        self.assertIn("summer", inf["season"])
        self.assertIn("spring", inf["season"])
        # Tags — useful broader set, not just ["casual"].
        self.assertIn("casual",  inf["tags"])
        self.assertIn("weekend", inf["tags"])
        self.assertIn("travel",  inf["tags"])


class TestCategoryFallbackTags(unittest.TestCase):
    """When text inference produces no occasion tags, the
    (category, formality) fallback table should supply a broader
    starter set than just a single tag."""

    def _canned(self, og_title):
        return {"success": True, "extracted": {
            "title": og_title, "og_title": og_title, "og_image": None,
            "og_description": "", "description": "", "jsonld_product": {},
        }, "error": None}

    def test_casual_top_gets_casual_weekend_travel(self):
        with mock.patch("link_import.fetch_url_metadata",
                        return_value=self._canned("Plain Crew T-Shirt")), \
             mock.patch("link_import.infer_color_from_image_url",
                        return_value=("", "low")):
            r = import_product_link("https://r.com/tee")
        tags = set(r["inferred"]["tags"])
        self.assertEqual(r["inferred"]["formality"], "casual")
        self.assertIn("casual",  tags)
        self.assertIn("weekend", tags)
        self.assertIn("travel",  tags)
        self.assertEqual(r["sources"]["tags"], "category-fallback")

    def test_smart_casual_blouse_gets_dinner_smart_casual_work(self):
        with mock.patch("link_import.fetch_url_metadata",
                        return_value=self._canned(
                            "Silk Button-Down Blouse")), \
             mock.patch("link_import.infer_color_from_image_url",
                        return_value=("", "low")):
            r = import_product_link("https://r.com/blouse")
        tags = set(r["inferred"]["tags"])
        self.assertEqual(r["inferred"]["formality"], "smart_casual")
        # silk + blouse / button-down → smart_casual; tags from table.
        self.assertTrue(tags & {"dinner", "smart_casual", "work"},
                        msg=f"got {tags}")

    def test_dress_gown_gets_formal(self):
        with mock.patch("link_import.fetch_url_metadata",
                        return_value=self._canned("Evening Gown")), \
             mock.patch("link_import.infer_color_from_image_url",
                        return_value=("", "low")):
            r = import_product_link("https://r.com/gown")
        self.assertEqual(r["inferred"]["formality"], "formal")
        # Tags either include "formal" (from category fallback) or
        # "evening" / "dinner" (from direct text inference). Both are
        # acceptable starting points the user can adjust.
        tags = set(r["inferred"]["tags"])
        self.assertTrue(tags & {"formal", "evening", "dinner"},
                        msg=f"got {tags}")


class TestSeasonInference(unittest.TestCase):
    """A t-shirt should not fall back to ['all']; it should land on
    spring/summer/fall (layering)."""

    def _canned(self, og_title):
        return {"success": True, "extracted": {
            "title": og_title, "og_title": og_title, "og_image": None,
            "og_description": "", "description": "", "jsonld_product": {},
        }, "error": None}

    def test_tshirt_season_includes_summer(self):
        with mock.patch("link_import.fetch_url_metadata",
                        return_value=self._canned("Crew Neck T-Shirt")), \
             mock.patch("link_import.infer_color_from_image_url",
                        return_value=("", "low")):
            r = import_product_link("https://r.com/tee")
        s = set(r["inferred"]["season"])
        self.assertTrue(s & {"summer", "spring"},
                        msg=f"got {r['inferred']['season']}")
        self.assertNotEqual(r["inferred"]["season"], ["all"])

    def test_cashmere_coat_is_winter(self):
        with mock.patch("link_import.fetch_url_metadata",
                        return_value=self._canned("Cashmere Coat")), \
             mock.patch("link_import.infer_color_from_image_url",
                        return_value=("", "low")):
            r = import_product_link("https://r.com/coat")
        s = set(r["inferred"]["season"])
        self.assertIn("winter", s)


if __name__ == "__main__":
    unittest.main(verbosity=2)
