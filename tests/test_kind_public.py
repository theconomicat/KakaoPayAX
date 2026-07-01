import unittest

from tools.collectors.kind_public import (
    _content_url_from_set_path,
    _selected_doc_no,
    parse_disclosure_rows,
)


DISCLOSURE_HTML = """
<section>
<table><tbody>
<tr>
  <td class="first txc" scope="row">1</td>
  <td class="txc">2026-03-10 16:30</td>
  <td><img alt='유가증권' class='vmiddle legend'> <a id="companysum" onclick="companysummary_open('00593');" title='삼성전자'>삼성전자</a></td>
  <td><a href="#viewer" onclick="openDisclsViewer('20260310001404','')" title='사업보고서(일반법인)'><font>[연결포함]</font>사업보고서(일반법인)</a></td>
  <td>삼성전자</td>
  <td></td>
</tr>
</tbody></table>
</section>
"""


VIEWER_HTML = """
<html><head><title>[삼성전자] 사업보고서(일반법인)</title></head>
<body>
<select id="mainDoc">
  <option value="">본문선택</option>
  <option value='20260310003123|Y'selected="selected">사업보고서(일반법인)</option>
</select>
</body></html>
"""


CONTENTS_HTML = """
<script>
parent.setPath('https://kind.krx.co.kr/external/toc.htm','https://kind.krx.co.kr/external/report.htm','/external/report','08','20');
</script>
"""


class KindPublicCollectorTests(unittest.TestCase):
    def test_parses_kind_disclosure_rows(self):
        rows = parse_disclosure_rows(DISCLOSURE_HTML)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].acpt_no, "20260310001404")
        self.assertEqual(rows[0].company, "삼성전자")
        self.assertIn("사업보고서", rows[0].title)
        self.assertIn("disclsviewer.do", rows[0].url)

    def test_detects_main_doc_number(self):
        self.assertEqual(_selected_doc_no(VIEWER_HTML), "20260310003123")

    def test_detects_kind_external_content_url(self):
        self.assertEqual(_content_url_from_set_path(CONTENTS_HTML), "https://kind.krx.co.kr/external/report.htm")


if __name__ == "__main__":
    unittest.main()
