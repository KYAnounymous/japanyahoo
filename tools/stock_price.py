import json
import re
from typing import Any, Dict
import requests
from bs4 import BeautifulSoup
from dify_plugin import Tool

class JapanStockPriceTool(Tool):
    def _invoke(self, tool_parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Dify プラグイン環境から Yahoo!ファイナンスへ直接アクセスして株価をパースします。
        プラグインノードのため、503プロキシブロックを受けずに外部通信が可能です。
        """
        ticker_code = str(tool_parameters.get("ticker_code", "")).strip().upper()
        
        if not re.match(r"^[A-Z0-9]{4}$", ticker_code):
            return {"error": "銘柄コードは4桁の半角英数字で指定してください（例: 7203、130A）。"}

        url = f"https://yahoo.co.jp{ticker_code}.T"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        try:
            # プラグイン環境からは、この外部リクエストが正常に通ります
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code != 200:
                return {"error": f"Yahoo!ファイナンスへのアクセスに失敗しました。(Status: {response.status_code})"}

            soup = BeautifulSoup(response.text, "html.parser")
            
            # JSON状態データの抽出
            script_tag = soup.find("script", string=re.compile(r"window\.__PRELOADED_STATE__\s*="))
            
            if script_tag and script_tag.string:
                json_text = re.search(r"window\.__PRELOADED_STATE__\s*=\s*(\{.*?\});", script_tag.string, re.DOTALL)
                if json_text:
                    state_data = json.loads(json_text.group(1))
                    quote_data = state_data.get("quote", {}).get(f"{ticker_code}.T", {})
                    
                    if quote_data:
                        return {
                            "ticker": ticker_code,
                            "company_name": quote_data.get("name", "不明な銘柄"),
                            "current_price": f"{quote_data.get('price', {}).get('current', 'N/A')} 円",
                            "price_change": str(quote_data.get("price", {}).get("change", "N/A")),
                            "price_change_percentage": f"{quote_data.get('price', {}).get('changePercentage', 'N/A')}%"
                        }

            # フォールバック処理
            title_tag = soup.find("h1")
            company_name = title_tag.text.strip() if title_tag else "不明な銘柄"
            company_name = re.sub(r"【[A-Z0-9]{4}】", "", company_name).strip()

            price_element = soup.select_one("[class*='_3862Zz04']") or soup.select_one("span._10ni79zM")
            price_text = price_element.text.strip() if price_element else "N/A"

            change_element = soup.select_one("[class*='_19v6_g2Y']") or soup.select_one("span._3rA9_9qA")
            change_text = change_element.text.strip() if change_element else "N/A"

            if price_text == "N/A" and company_name == "不明な銘柄":
                return {"error": f"銘柄コード {ticker_code} の有効なデータを取得できませんでした。"}

            return {
                "ticker": ticker_code,
                "company_name": company_name,
                "current_price": f"{price_text} 円",
                "price_change": change_text,
                "price_change_percentage": "N/A (Fallback)"
            }

        except Exception as e:
            return {"error": f"プラグイン実行中にエラーが発生しました: {str(e)}"}
