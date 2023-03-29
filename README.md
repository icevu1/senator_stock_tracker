# senator_stock_tracker
Web scrapper that watches https://www.capitoltrades.com/trades for new trades made by USA senator's in case you want
to copy their action with your own portfolio. They often have priviledged information not accessible to the public, so it's a good idea to be up to date to their actions in the stock market.


The web scrapper also include oauth2 to link your email address to your gmail account to be able to continiously receive
emails with any new trades that gets posted.

Make sure to make a .env file with TO_EMAIL (your email address) and CLIENT_SECRET_FILE (file given by gmail's API)

You can also change the WATCH_INTERVAL variable to increase how often the script looks for new postings on the original website. (Default is 60 seconds)
