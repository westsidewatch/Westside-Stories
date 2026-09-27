"""Local Chinese church-language context for subtitle proofreading."""
from __future__ import annotations

SCRIPTURE_BOOKS = (
    "創世記 出埃及記 利未記 民數記 申命記 約書亞記 士師記 路得記 撒母耳記 列王紀 歷代志 "
    "以斯拉記 尼希米記 以斯帖記 約伯記 詩篇 箴言 傳道書 雅歌 以賽亞書 耶利米書 耶利米哀歌 "
    "以西結書 但以理書 何西阿書 約珥書 阿摩司書 俄巴底亞書 約拿書 彌迦書 那鴻書 哈巴谷書 "
    "西番雅書 哈該書 撒迦利亞書 瑪拉基書 馬太福音 馬可福音 路加福音 約翰福音 使徒行傳 "
    "羅馬書 哥林多前書 哥林多後書 加拉太書 以弗所書 腓立比書 歌羅西書 帖撒羅尼迦前書 "
    "帖撒羅尼迦後書 提摩太前書 提摩太後書 提多書 腓利門書 希伯來書 雅各書 彼得前書 "
    "彼得後書 約翰一書 約翰二書 約翰三書 猶大書 啟示錄"
).split()

BIBLICAL_NAMES = (
    "亞伯拉罕 以撒 雅各 約瑟 摩西 亞倫 約書亞 撒母耳 掃羅 大衛 所羅門 以利亞 以利沙 "
    "以賽亞 耶利米 以西結 但以理 以斯拉 尼希米 施洗約翰 耶穌 基督 彼得 約翰 雅各 保羅 "
    "巴拿巴 提摩太 提多 亞波羅 司提反 馬利亞 馬大 拉撒路 麥基洗德 尼布甲尼撒 所羅巴伯 "
    "耶路撒冷 伯利恆 拿撒勒 加利利 撒馬利亞 猶太 伯特利 希伯崙 迦百農 哥各他 橄欖山 錫安 錫安山"
).split()

THEOLOGY_AND_CHURCH = (
    "福音 救恩 救贖 恩典 恩召 呼召 蒙召 揀選 稱義 成聖 得榮耀 悔改 信心 盼望 復活 永生 "
    "十字架 寶血 贖罪 挽回祭 施恩座 約 應許 律法 先知 祭司 君王 聖殿 會幕 約櫃 逾越節 "
    "五旬節 聖靈 聖靈充滿 聖靈感動 三位一體 天國 神的國 主禱文 大使命 門徒 使徒 "
    "教會 牧師 傳道 長老 執事 弟兄 姊妹 肢體 團契 牧養 事奉 服事 主日 崇拜 敬拜 讚美 "
    "禱告 代禱 見證 奉獻 洗禮 浸禮 聖餐 查經 主日學 講道 經文 章 節 和合本 錫安堂"
).split()


def vocabulary() -> list[str]:
    return list(dict.fromkeys(SCRIPTURE_BOOKS + BIBLICAL_NAMES + THEOLOGY_AND_CHURCH))


def context_payload() -> dict:
    return {
        "schema": "westside.church-language-context.v2",
        "language": "zh-Hant",
        "domain": "Chinese Christian sermon and Bible teaching",
        "preserve_spoken_wording": True,
        "terms": vocabulary(),
    }
