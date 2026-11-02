"""Independent content, numerical-parity and broken-link checks."""
import json
import math
import unittest
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit
import build

ROOT = Path(__file__).resolve().parent

class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.titles = []
        self.in_h1 = False
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'h1': self.in_h1 = True
        for key in ('href', 'src'):
            if attrs.get(key): self.links.append(attrs[key])
    def handle_endtag(self, tag):
        if tag == 'h1': self.in_h1 = False
    def handle_data(self, data):
        if self.in_h1: self.titles.append(data)

class PersonalSiteTests(unittest.TestCase):
    def test_python_recomputed_monthly_values_match_approved_charts(self):
        expected = json.loads((ROOT / 'chart-reference.json').read_text())
        rows = build.read_weather()
        for item in build.monthly_summary(rows):
            ref = expected[str(item['month'])]
            self.assertEqual(item['count'], ref['count'])
            self.assertTrue(math.isclose(item['tmax_mean'], ref['tmax_mean'], abs_tol=1e-10))
            self.assertTrue(math.isclose(item['prcp_mean'], ref['prcp_mean'], abs_tol=1e-10))
    def test_every_local_link_and_asset_exists(self):
        for name in ('index.html','myresume.html','plotly.html','dashboard.html'):
            parser = Links()
            parser.feed((ROOT / 'docs' / name).read_text())
            for link in parser.links:
                url = urlsplit(link)
                if url.scheme or url.netloc or not url.path: continue
                self.assertTrue((ROOT / 'docs' / unquote(url.path)).exists(), (name, link))
    def test_identity_resume_and_updated_contact_information(self):
        profile = json.loads((ROOT / 'profile.json').read_text())
        home = (ROOT / 'docs/index.html').read_text()
        self.assertIn('<h1>徐乔依</h1><p class="subtitle">Joyce</p>', home)
        resume = (ROOT / 'docs/myresume.html').read_text()
        for item in (profile['email'], profile['phone'], 'Peking University', 'Pharmaron Clinical'):
            self.assertIn(item, resume)
        self.assertNotIn('Publish an essay',resume)
        self.assertEqual(len(profile['jobs'][1]['roles'][0]['bullets']),3)
    def test_three_charts_on_each_visualization_page(self):
        for name, prefix in [('plotly.html','plot-'),('dashboard.html','dashboard-')]:
            text = (ROOT / 'docs' / name).read_text()
            for i in range(3): self.assertIn(f'id="{prefix}{i}"',text)
    def test_no_r_or_quarto_build_sources(self):
        for glob in ('*.R','*.Rmd','*.qmd','*.Rproj','_quarto.yml'):
            self.assertEqual(list(ROOT.glob(glob)),[])

if __name__ == '__main__':
    unittest.main()
