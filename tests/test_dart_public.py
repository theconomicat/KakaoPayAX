import unittest

from tools.collectors.dart_public import (
    parse_report_toc,
    parse_search_results,
    parse_xbrl_roles,
    select_financial_documents,
)


SEARCH_HTML = """
<table><tbody>
<tr>
  <td>1</td>
  <td class="tL"><a href="javascript:openCorpInfoNew('00126380', 'winCorpInfo', '/dsae001/selectPopup.ax');">삼성전자</a></td>
  <td class="tL">
    <a href="/dsaf001/main.do?rcpNo=20260310002820" id="r_20260310002820">사업보고서 (2025.12)</a>
    <img onclick="openXbrlViewerNew('https://opendart.fss.or.kr','20260310002820','Y','Y');">
  </td>
  <td class="tL ellipsis" title="삼성전자">삼성전자</td>
  <td>2026.03.10</td>
  <td><span>연</span></td>
</tr>
</tbody></table>
"""


TOC_JS = """
var node2 = {};
node2['text'] = "2. 연결재무제표";
node2['rcpNo'] = "20260310002820";
node2['dcmNo'] = "11104488";
node2['eleId'] = "19";
node2['offset'] = "376820";
node2['length'] = "258279";
node2['dtd'] = "dart4.xsd";
var node3 = {};
node3['text'] = "2-1. 연결 재무상태표";
node3['rcpNo'] = "20260310002820";
node3['dcmNo'] = "11104488";
node3['eleId'] = "20";
node3['offset'] = "376968";
node3['length'] = "55064";
node3['dtd'] = "dart4.xsd";
var node3 = {};
node3['text'] = "3. 연결재무제표 주석";
node3['rcpNo'] = "20260310002820";
node3['dcmNo'] = "11104488";
node3['eleId'] = "25";
node3['offset'] = "635103";
node3['length'] = "2100360";
node3['dtd'] = "dart4.xsd";
"""


XBRL_HTML = """
<a href="javascript:void(0);" id="role_D210000" onclick="viewDoc('20260310000011', 'dart_2024-06-30_role-D210000', 'ko', 'D210000')">
  <!-- [D210000] 재무상태표, 유동/비유동법 - 연결 -->
  재무상태표, 유동/비유동법 - 연결
</a>
<a href="javascript:void(0);" id="role_D822380" onclick="viewDoc('20260310000011', 'dart_2024-06-30_role-D822380', 'ko', 'D822380')">
  28. 재무위험관리
</a>
"""


class DartPublicCollectorTests(unittest.TestCase):
    def test_parses_public_search_results_with_corp_code_and_xbrl(self):
        reports = parse_search_results(SEARCH_HTML, "사업보고서")
        self.assertEqual(len(reports), 1)
        self.assertEqual(reports[0].corp_code, "00126380")
        self.assertEqual(reports[0].rcp_no, "20260310002820")
        self.assertTrue(reports[0].xbrl_available)

    def test_selects_financial_documents_from_report_toc(self):
        documents = parse_report_toc(TOC_JS, "20260310002820")
        selected = select_financial_documents(documents, max_documents=2)
        self.assertGreaterEqual(len(documents), 3)
        self.assertTrue(any("재무상태표" in document.title for document in selected))
        self.assertTrue(all("viewer.do" in document.url for document in selected))

    def test_parses_xbrl_viewer_roles(self):
        roles = parse_xbrl_roles(XBRL_HTML)
        self.assertEqual(len(roles), 2)
        self.assertEqual(roles[0].xbrl_ext_seq, "20260310000011")
        self.assertIn("roleId=dart_2024-06-30_role-D210000", roles[0].url)


if __name__ == "__main__":
    unittest.main()
