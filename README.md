# MyGO!!!!! Line Search Discord Bot
An attempt to port [MyGO 台詞搜尋 Discord 機器人](https://github.com/eason102/mygo_serifu_bot) into an English version.

All features of the Chinese version are supported.

### [Invite link](https://discord.com/oauth2/authorize?client_id=1348243637380583476)

## **Searching**

You can search by fields:
- episode, ep, e
- show, series, s
  - valid values are "mygo" and "ave mujica"
- actor, name, n
  - does not work for "ave mujica"
- text
- start
- end

Basic examples are:
- show:mygo name:anon chihaya anon
- show:"ave mujica" doloris

Of course, you can just search without the fields, like:
- mygo anon cute pens
- tomori penguin

and it'll still search correctly.
By default, the bot searches the `show`, `name`, and `text` field when not specified.

You can learn more about the query syntax [here](https://whoosh.readthedocs.io/en/latest/querylang.html).

---

## **Source**

- Extract subtitles with `ffmpeg` and parse using `pysubs2`
- Convert video files to GIFs and images with `ffmpeg`


### TODO

- Metrics
- Fix start/end/duration search
- Multi-line search
- Custom user-submitted scenes?

---

# Below are the original previews and part of the original README.

---

## **效果展示**

**支援動態搜尋台詞**：  
![動態搜尋效果](https://github.com/eason102/mygo_serifu_bot/blob/main/images/2024-12-10%2013-52-11%20(1).gif?raw=true)  

**可自訂截圖延後時間，精準捕捉角色表情**：  (Customize screenshots to delay time, accurately capture character expressions)
![延後截圖效果](https://github.com/eason102/mygo_serifu_bot/blob/main/images/2024-12-10%2013-52-31%20(1).gif?raw=true)  

**可自訂義時長製作GIF**：
![GIF製作](https://github.com/eason102/mygo_serifu_bot/blob/main/images/GIF.gif?raw=true)  

---

## **資料來源**

- 使用 VirtualDruid 提供的 OCR 資料  
- 搭配 `ffmpeg` 對原檔進行截圖  
- 畫面來源：動畫瘋


### TODO

統計網頁