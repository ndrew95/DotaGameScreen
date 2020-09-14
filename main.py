#Author: Nicholas Shipley
#Date: August 26th, 2020
#Program: Dota victory screen and scorescreen display

import pymongo
import math
import requests
import json
import time
import Tkinter as tk
from Tkinter import *
import sys
import os
import threading
from pydub import AudioSegment
from pydub.playback import play


#global variables containing the MongoDB information to access
client = pymongo.MongoClient("Info-Here")
db = client.dota2
matches = db.matches



def main():

	count = 0
	goAhead = False
	dupli = True
	matchDetails = db.matchDetails


	while dupli == True:

		stop=False
		count1 = 0
		count = 0
		goAhead = False

		#this try-statement is a make-shift API listener. This try statement will continue to ping
		#the dota servers every 13 seconds to ensure that new game data is retrieved in ample time.
		#13 seconds was used, as it was the shortest amount of time allowed by 1) Valve's API and 2) the 
		#programs run-time.
		try:		

			time.sleep(13)
			responsePlayer = requests.get("https://api.steampowered.com/IDOTA2Match_570/GetMatchHistory/V001/?key=[YOURKEY]&account_id=[YOURACCTID]&matches_requested=1").json()

		except:

			#frequently, Valve's API goes offline. Since a traditional API listener package was not used, an
			#exception is thrown if the API is offline. If the API is offline, the function is called, and the
			#API is pinged again to see if it is online.

			main()

		match = responsePlayer["result"]["matches"]
		matchIDPlayer = responsePlayer["result"]["matches"]
		matchIDPlayer = matchIDPlayer[0]["match_id"]

		#This try-statement checks retrieves the match ID of the current match. As the last try-except statement
		#only received the player details, this try-except statement matches the player with the game information.
		#Again, as the API can be offline, a try-except is utilized.
		try:

			time.sleep(1)
			matchCurrent = """http://api.steampowered.com/IDOTA2Match_570/GetMatchDetails/v1/?key=[YOURKEY]&match_id=%s"""%(matchIDPlayer)

		except:

			main()

		matchResponse = requests.get(matchCurrent).json()


		#Here, we check if the database already contains the match information. If the database already holds
		#the information, then we do not want to execute the following code, otherwise old scorescreens
		#would be shown repeatedly.
		matchExists = matches.find_one({ "match_id": matchIDPlayer, "players.account_id": [YOURACCTID] })


		#If the match does not exist, "goAhead" is set to true, to avoid repeated scorescreens, goAhead is initially
		#set to false.
		if not(matchExists):
			goAhead = True

			#the current match is inserted into the MongoDB database, to ensure scorescreens aren't
			#repeatedly shown.
			matches.insert_many(match)

			#Match details are also inserted into the database to be retreived for the scorescreen.
			matchDetails.insert_one(matchResponse)


		#With the match details, these two lines of code check if the player won.
		#If the player's ID was over 120 and radiant win is false, the player won.
		#If a player's ID was less than 120, and radiant win is true, the player won.
		winsDirePlayer = matchDetails.find(  {"$and": [ {"result.players.player_slot": {"$gt": 128} , "result.players.account_id":  [YOURID]} ] , "result.radiant_win" : False, "result.match_id": matchIDPlayer} )
		winsRadPlayer = matchDetails.find(  {"$and" : [  {"result.players.player_slot": {"$lt": 5 } , "result.players.account_id":  [YOURID]} ], "result.radiant_win" : True , "result.match_id": matchIDPlayer}  )


		heroPlayed = []
		#These for-loops check if radiant or dire won, and also append each hero that was played into a list.
		#As heroes are stored as an ID, the ID's will later be used to output the hero name.
		for x in winsRadPlayer:
			for i in range(0,10):
				if x["result"]["players"][i]["player_slot"] < 5 and x["result"]["players"][i]["account_id"]==[YOURID]:
					radiWin = True

				heroPlayed.append(x["result"]["players"][i])


		for x in winsDirePlayer:
			for i in range(0,10):
				if x["result"]["players"][i]["player_slot"] > 5 and x["result"]["players"][i]["account_id"]==[YOURID]:
					direWin = True

				heroPlayed.append(x["result"]["players"][i])

		
		#If the player won, either as radiant or dire, and the match is not an already existing match,
		#this if-statement will be True.
		if  (direWin == True or radiWin == True) and goAhead == True:

			#If the player won as Dire, a Dire victory video is played on the computer,
			#If the player won as radiant, a radiant victory video is shown.
			if direWin == True:

				movie_path = "direvictory.mp4"
				from subprocess import Popen
				omxp = Popen(["omxplayer",movie_path])

			if radiWin == True:

				movie_path = "radiantvictory.mp4"
				from subprocess import Popen
				omxp = Popen(["omxplayer",movie_path])

			

			#if a player did win in a game not yet recorded, the "start" function is called to show the
			#score screen. It passes in the heroPlayed list as an argument so the function can
			#decipher the heroes played by ID
			scoreScreen(heroPlayed)


		#if the match is new, yet the player did not win, the scorescreen is still shown.
		if goAhead == True:
			scoreScreen(heroPlayed)

def scoreScreen(Hero):

	#This function is paused for 12 seconds, which is the length of the video. This pause ensures
	#that the scorescreen isn't displayed ontop of the victory video.
	start = time.time() + 12

	#retreiving hero information from the MongoDB database.
	heroes = db.heroes
	heroList = heroes.find()



	heroListName = []
	#This for-loop deciphers which hero was played based on the heroID retreived from Valve's API
	for x in heroList:
		heroListName.append(x["id"])

		if len(str(x["name"]).split("_")[3]) <14:
			minus14 = 14 - len(str(x["name"]).split("_")[3])
			heroListName.append(str(x["name"]).split("_")[3] + str("  "*minus14))

		else:
			heroListName.append(str(x["name"]).split("_")[3])





	#The following code creates a dictionary which links, from data from Valve's API, which hero played
	#in the game had what stats, including kills, deaths, assists, kill-participation (KP), Last Hits, Denies
	#GPM, and Damage.
	a = {}
	count = 1
	a[0] = "Radiant\n\n Hero         \t\t\t\t\tKills\tDeaths\tAssists\tKP\tLast Hits\tDenies\tGPM\tDamage\n"
	totalDamageDire = 0
	totalDamageRadiant = 0
	killsDire = 0
	killsRad = 0
	assistsDire = 0
	assistsRad = 0
	lastDire = 0
	lastRad = 0
	denyDire = 0
	denyRad = 0
	gpmDire = 0
	gpmRad = 0
	deathsDire = 0
	deathsRad = 0
	killAssI = 0 

	for i in Hero:

		index = i["hero_id"]
		key = count

		index1 = heroListName.index(index)
		killpartRad = Hero[0]["kills"]+Hero[1]["kills"]+Hero[2]["kills"]+Hero[3]["kills"]+Hero[4]["kills"]
		killpartDire = Hero[5]["kills"]+Hero[6]["kills"]+Hero[7]["kills"]+Hero[8]["kills"]+Hero[9]["kills"]
		killsAndAssists = i['kills'] + i['assists']
		killsAndAssists = float(killsAndAssists)

		if count<6:
			killAssI = math.ceil(killsAndAssists/killpartRad*100)
			print(killAssI)
		if count>=6:
			killAssI = math.ceil(killsAndAssists/killpartDire*100)

		value = str(heroListName[index1+1]) + "\t\t\t\t\t" + str(i["kills"]) + "\t" + str(i["deaths"]) + "\t" + str(i["assists"]) + "\t" + str(killAssI) + "\t" + str(i["last_hits"]) + "\t" + str(i["denies"]) + "\t" + str(i["gold_per_min"]) +  "\t" + str(i["hero_damage"]) + "\n"

		a[key] = value
		
		if count<6:
			totalDamageRadiant+=i["hero_damage"]
			killsRad+=i["kills"]
			assistsRad+=i["assists"]
			lastRad+=i["last_hits"]
			denyRad+=i["denies"]
			gpmRad+=i["gold_per_min"]
			deathsRad+=i["deaths"]
		if count>=6:
			totalDamageDire+=i["hero_damage"]
			killsDire+=i["kills"]
			assistsDire+=i["assists"]
			lastDire+=i["last_hits"]
			denyDire+=i["denies"]
			gpmDire+=i["gold_per_min"]
			deathsDire+=i["deaths"]

		count+=1


	#Creating the Tkinter labels
	w1 = tk.Label(root, font=("Helvetica", 11), justify="left",  width=root.winfo_screenwidth(),  text=a[0])
	w2 = tk.Label(root, font=("Helvetica", 11), justify="left",  width=root.winfo_screenwidth(),  text=a[1])
	w3 = tk.Label(root, font=("Helvetica", 11), justify="left",  width=root.winfo_screenwidth(),  text=a[2])
	w4 = tk.Label(root, font=("Helvetica", 11), justify="left",  width=root.winfo_screenwidth(),  text=a[3])
	w5 = tk.Label(root, font=("Helvetica", 11), justify="left",  width=root.winfo_screenwidth(),  text=a[4])
	w6 = tk.Label(root, font=("Helvetica", 11), justify="left", underline=1,  width=root.winfo_screenwidth(),  text=a[5].strip("\n"))
	w7 = tk.Label(root, font=("Helvetica", 11), justify="left",  width=root.winfo_screenwidth(),  text="\n\nDire\n\n Hero         \t\t\t\t\tKills\tDeaths\tAssists\tKP\tLast Hits\tDenies\tGPM\tDamage\n")
	w8 = tk.Label(root, font=("Helvetica", 11), justify="left",  width=root.winfo_screenwidth(),  text=a[6])
	w9 = tk.Label(root, font=("Helvetica", 11), justify="left",  width=root.winfo_screenwidth(),  text=a[7])
	w10 = tk.Label(root, font=("Helvetica", 11), justify="left",  width=root.winfo_screenwidth(),  text=a[8])
	w11 = tk.Label(root, font=("Helvetica", 11), justify="left", underline=1,  width=root.winfo_screenwidth(),  text=a[9])
	w12 = tk.Label(root, font=("Helvetica", 11), justify="left",  width=root.winfo_screenwidth(),  text=a[10].strip("\n"))
	w13 = tk.Label(root, font=("Arial", 11), justify="left",  width=root.winfo_screenwidth(),  text="Total           \t\t\t\t\t" + str(killsRad) + "\t" + str(deathsRad) + "\t" + str(assistsRad) + "\t" + str("N/A") + "\t" + str(lastRad) + "\t" + str(denyRad) + "\t" + str(gpmRad) + "\t" + str(totalDamageRadiant))
	w14 = tk.Label(root, font=("Arial", 11), justify="left",  width=root.winfo_screenwidth(),  text="Total           \t\t\t\t\t" + str(killsDire) + "\t" + str(deathsDire) + "\t" + str(assistsDire) + "\t" + str("N/A") + "\t" + str(lastDire) + "\t" + str(denyDire) + "\t" + str(gpmDire) + "\t" + str(totalDamageDire))
	w15 = tk.Label(root, font=("Arial", 11), height=0, justify="left",  width=root.winfo_screenwidth(),  text=str("__"*(len(a[0]))) )
	w16 = tk.Label(root, font=("Arial", 11), height=0, justify="left",  width=root.winfo_screenwidth(),  text= str("__"*(len(a[0]))) )

	root.geometry("{0}x{1}+0+0".format(root.winfo_screenwidth(), root.winfo_screenheight()))

	root.pack_propagate(0)

	#"Packing" the Tkinter labels
	w1.pack(fill="x", anchor="w")
	w2.pack(fill="x", anchor="w")
	w3.pack(fill="x", anchor="w")
	w4.pack(fill="x", anchor="w")
	w5.pack(fill="x", anchor="w")
	w6.pack(fill="x", anchor="w")
	w7.pack(fill="x", anchor="w")
	w8.pack(fill="x", anchor="w")
	w9.pack(fill="x", anchor="w")
	w10.pack(fill="x", anchor="w")
	w11.pack(fill="x", anchor="w")
	w12.pack(fill="x", anchor="w")
	w13.pack(fill="x", anchor="w")
	w14.pack(fill="x", anchor="w")
	w15.pack(fill="x", anchor="w")
	w16.pack(fill="x", anchor="w")



	LOOP_ACTIVE = True

	#This loop will execute once all Tkinter aspects have been initialized.
	#The loop updates the root of Tkinter, which displays the scorescreen, and then
	#sleeps for 60 seconds, allowing the user to adequately examine the scorescreen.
	#After 60 seconds, the program restarts, and continues to "listen" for new game data.
	while LOOP_ACTIVE:

		if time.time()>start:

			root.update()
			time.sleep(60)

			os.execv(sys.executable, [sys.executable] + sys.argv)
