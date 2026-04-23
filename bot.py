import asyncio, logging, json, os, aiohttp
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

BOT_TOKEN = "8618492241:AAEPF0cqEk4qtbz3Xw38dIMq-XHUTqiYqCE"
DATA_FILE = os.path.expanduser("~/neuroxx/data.json")
DEX_API = "https://api.dexscreener.com/token-profiles/latest/v1"
RUGCHECK_API = "https://api.rugcheck.xyz/v1/tokens/{}/report"
GROUP_ID = -1003977332415

logging.basicConfig(level=logging.WARNING)
SCAM_WORDS = ["DO NOT","SCAM","FAKE","WARN","HONEYPOT","RUGGED","TEST"]

def load():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE) as f: return json.load(f)
    return {"subscribers": [1839443374]}

def save(d):
    with open(DATA_FILE, "w") as f: json.dump(d, f)

def add_sub(uid):
    d = load()
    if uid not in d["subscribers"]:
        d["subscribers"].append(uid)
        save(d)

def fmt(n):
    if n is None: return "N/A"
    if n >= 1_000_000: return f"${n/1_000_000:.1f}M"
    if n >= 1_000: return f"${n/1_000:.1f}K"
    return f"${n:.2f}"

async def get_rugcheck(session, addr):
    try:
        async with session.get(RUGCHECK_API.format(addr), timeout=aiohttp.ClientTimeout(total=5)) as r:
            if r.status == 200:
                return await r.json()
    except: pass
    return None

async def get_dex_info(session, chain, addr):
    try:
        url = f"https://api.dexscreener.com/latest/dex/tokens/{addr}"
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as r:
            d = await r.json()
            pairs = d.get("pairs")
            if pairs:
                p = pairs[0]
                return {
                    "symbol": p.get("baseToken",{}).get("symbol","???"),
                    "name": p.get("baseToken",{}).get("name","Unknown"),
                    "mc": p.get("fdv"),
                    "link": p.get("url", f"https://dexscreener.com/{chain}/{addr}")
                }
    except: pass
    return None

async def fetch_tokens():
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(DEX_API) as r:
                data = await r.json()
                print(f"[DEX] {len(data)} tokens")
                return data
    except Exception as e:
        print(f"[ERR] {e}")
        return []

def holder_emoji(pct):
    if pct < 20: return "🟢"
    if pct < 40: return "🟡"
    return "🔴"

async def send_calls(app):
    seen = set()
    while True:
        tokens = await fetch_tokens()
        async with aiohttp.ClientSession() as session:
            for t in tokens[:10]:
                addr = t.get("tokenAddress","")
                chain = t.get("chainId","")
                desc = t.get("description","").upper()
                if not addr or addr in seen: continue
                if any(w in desc for w in SCAM_WORDS): continue
                seen.add(addr)
                dex = await get_dex_info(session, chain, addr)
                if not dex: continue
                rug = await get_rugcheck(session, addr)
                symbol = dex["symbol"]
                name = dex["name"]
                mc = fmt(dex["mc"])
                chart_link = dex["link"]
                if rug:
                    score = rug.get("score", 0)
                    risks = rug.get("risks", [])
                    holders = rug.get("topHolders", [])
                    total_holders = rug.get("totalHolders", 0)
                    top10_pct = round(sum(h.get("pct",0) for h in holders[:10]), 1)
                    dev_holding = round((holders[0].get("pct",0)), 2) if holders else 0
                    if score > 600: seen.discard(addr); continue
                    rug_risk = "LOW 🟢" if score < 300 else "MED 🟡" if score < 600 else "HIGH 🔴"
                    h_emoji = holder_emoji(top10_pct)
                    gmgn = f"https://gmgn.ai/sol/token/{addr}"
                    trojan = f"https://t.me/trojanbot?start={addr}"
                    axiom = f"https://axiom.trade/t/{addr}"
                    text = (
                        f"🌕 [PUMP] {name} (${symbol})\n"
                        f"✨ `{addr}`\n"
                        f"├MC:       {mc} [📊CHART]({chart_link})\n"
                        f"├Rug rate: {rug_risk}\n"
                        f"├Holders:  {total_holders}|Top10: {top10_pct}% {h_emoji}\n"
                        f"├Devs:      {dev_holding}%\n"
                        f"└Risks: {len(risks)} found\n\n"
                        f"🚀 [GMGN]({gmgn}) • [Trojan]({trojan}) • [AXIOM]({axiom})\n"
                        f"➖➖➖➖➖➖➖➖\n"
                        f"📡 *NEUROXX CRYPTO CALLS*"
                    )
                else:
                    text = (
                        f"🌕 [PUMP] {name} (${symbol})\n"
                        f"✨ `{addr}`\n"
                        f"├MC: {mc} [📊CHART]({chart_link})\n"
                        f"├Chain: {chain.upper()}\n\n"
                        f"🚀 [DexScreener]({chart_link})\n"
                        f"➖➖➖➖➖➖➖➖\n"
                        f"📡 *NEUROXX CRYPTO CALLS*"
                    )
                targets = load()["subscribers"] + [GROUP_ID]
                for uid in targets:
                    try:
                        await app.bot.send_message(uid, text, parse_mode="Markdown", disable_web_page_preview=True)
                        print(f"[SENT] {uid}")
                    except Exception as e:
                        print(f"[ERR] {uid}: {e}")
                await asyncio.sleep(2)
        await asyncio.sleep(15)

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    add_sub(update.effective_user.id)
    await update.message.reply_text("✅ Subscribed! Calls milne lagengi!")

async def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    async with app:
        await app.start()
        await app.updater.start_polling()
        await send_calls(app)

if __name__ == "__main__":
    asyncio.run(main())