# 🚀 Railway Deployment Guide

## 📋 **Step-by-Step Railway Setup**

### **Step 1: Create Railway Account**
1. Go to [railway.app](https://railway.app)
2. Sign up with GitHub
3. Create a new project

### **Step 2: Connect Your Repository**
1. Click "Deploy from GitHub repo"
2. Select your repository
3. Railway will automatically detect it's a Python project

### **Step 3: Set Environment Variables**
In Railway dashboard, go to "Variables" tab and add:

```
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
ENABLE_TRANSLATION=true
DEFAULT_CURRENCY=EUR
MIN_HOURS_BETWEEN_REPOSTS=72
```

### **Step 4: Deploy**
1. Railway will automatically deploy when you push to GitHub
2. Or click "Deploy Now" in Railway dashboard

### **Step 5: Monitor**
1. Check "Deployments" tab for build status
2. Check "Logs" tab for bot output
3. Monitor your Telegram channel for deals

---

## 🔧 **Troubleshooting**

### **Issue: Playwright Installation Fails**
- **Solution:** The bot will work without Playwright (only Verkkokauppa needs it)
- **Alternative:** Bot will skip dynamic sites and focus on Prisma/Tokmanni

### **Issue: Environment Variables Missing**
- **Solution:** Make sure all variables are set in Railway dashboard
- **Check:** Look at logs for "Missing required environment variables"

### **Issue: Bot Not Starting**
- **Solution:** Check logs in Railway dashboard
- **Common cause:** Missing Telegram credentials

### **Issue: No Deals Found**
- **Solution:** Check if store websites changed
- **Monitor:** Look at logs for parsing errors

---

## 📊 **Expected Behavior**

### **Successful Deployment:**
```
🚀 Starting Finnish Deals Bot on Railway...
🔧 Setting up Playwright browsers...
✅ Playwright setup completed!
✅ Environment variables configured
🤖 Starting bot in loop mode...
2025-08-24 16:20:14 [INFO] Scanning Prisma – https://www.prisma.fi/kampanjat/ale
2025-08-24 16:20:15 [INFO] Parsed 47 products from Prisma
...
2025-08-24 16:20:49 [INFO] Done. Announced 3 deals (>= 10%).
```

### **Bot Will:**
- ✅ Run every 12 hours automatically
- ✅ Find deals from Prisma, Tokmanni, Verkkokauppa
- ✅ Translate Finnish to English
- ✅ Post to your Telegram channel
- ✅ Avoid duplicate posts

---

## 🎯 **Success Indicators**

1. **Railway Dashboard:** Shows "Deployed" status
2. **Logs:** Show bot scanning stores and finding deals
3. **Telegram:** Receive deal messages every 12 hours
4. **No Errors:** Clean logs without major errors

---

## 🆘 **Need Help?**

If deployment fails:
1. Check Railway logs for specific errors
2. Verify environment variables are set correctly
3. Make sure your Telegram bot token is valid
4. Test locally first with `python fin_deals_bot.py --run-once`

**Your bot will work perfectly once deployed!** 🚀
