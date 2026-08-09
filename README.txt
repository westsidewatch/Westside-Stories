Westside Stories 1.0

這是正式 1.0 專案包。

已加入：
- 繁體中文 + English 介面
- 品牌 Welcome 首頁
- 哈巴谷書 2:2
- 初光金 / Ink Black 品牌配色
- 聖殿石背景素材
- About 視窗
- 教會版權資訊
- Whisper → SRT → FFmpeg 完整流程
- 行首標點修正：字幕行不會以 ，。！？：；、… 等標點開頭
- DMG 建立腳本

使用：
1. 解壓 ZIP。
2. Terminal 輸入：chmod +x 
3. 把 build_app.command 拖進 Terminal，按 Enter。
4. 雙擊 build_app.command。
5. 完成後測試 dist/Westside Stories.app。
6. App 確認正常後，雙擊 create_dmg.command。
7. 會生成 Westside-Stories-1.0.dmg。

注意：
此專案包本身不含字體檔。
App 會優先使用系統已安裝的 Cormorant Garamond 與 Noto Serif TC。


Release adjustment:
- 繁體中文介面統一使用有襯線字體。
- 首選 Noto Serif TC（與 Westside Watch Join 同款）。
- 未安裝 Noto Serif TC 時，以 macOS 的 Songti TC 作為有襯線備援。
- 英文品牌標題與英文經文維持 Cormorant Garamond。
