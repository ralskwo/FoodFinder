from crawlers import naver_place
from crawlers.naver_place import NaverPlaceCrawler


def test_extract_menus_fallback_without_bs4(monkeypatch):
    crawler = NaverPlaceCrawler()
    monkeypatch.setattr(naver_place, "BeautifulSoup", None)

    html = """
    <html><head></head><body>
      <script id="__NEXT_DATA__" type="application/json">
      {
        "props": {
          "pageProps": {
            "menus": [
              {"menuName": "Kimchi Jjigae", "menuPrice": "9000"},
              {"menuName": "Pork Cutlet", "menuPrice": "11000"}
            ]
          }
        }
      }
      </script>
    </body></html>
    """

    menus = crawler._extract_menus(html)
    assert len(menus) >= 2
    assert menus[0]["name"] in {"Kimchi Jjigae", "Pork Cutlet"}
    assert menus[0]["price"] in {9000, 11000}
