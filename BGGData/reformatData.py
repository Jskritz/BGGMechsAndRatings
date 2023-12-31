import math
import pandas as pd
import numpy as np
def repeatUniqueGameIDS(df):
    # repeating all values for game ID except mechanics and implementations
    lastGameID = 0
    countIndexes = []
    data = {}
    for series_name, series in df.items():
        # print(series_name)
        if series_name != "implementation" and series_name != "mechanic":
            data[series_name] = []
        else:
            continue
        gameIDCounter = 0
        skipCounter = 0
        for element in series:
            # print(element)
            if series_name == "gameID":
                currentGameID = element
                if currentGameID != lastGameID:
                    # count = count + 1
                    lastGameID = currentGameID
                    data[series_name].append(currentGameID)
                    countIndexes.append(series.value_counts()[currentGameID])
                    # if (count > 10):
                    #     count = 0
                    #     break
            elif series_name != "implementation" and series_name != "mechanic":
                print(gameIDCounter)
                if skipCounter == 0:
                    # count = count + 1
                    if (not pd.isna(element)):
                        currentValue = element
                        data[series_name].append(currentValue)
                    else:
                        data[series_name].append(np.nan)

                if skipCounter < (countIndexes[gameIDCounter] - 1):
                    skipCounter = skipCounter + 1
                else:
                    skipCounter = 0
                    gameIDCounter = gameIDCounter + 1
                # if (count > 10):
                #     count = 0
                #     break
    return pd.DataFrame(data)

def addMechanics(df):
    reformated = df.groupby('gameID').first().reset_index()
    reformated = reformated.drop(["mechanic", "implementation"], axis=1)
    mechlist = df['mechanic'].unique()
    mechlist = np.delete(mechlist, 0)
    gameIDList = reformated["gameID"].unique()
    data = {}
    for mechanic in mechlist:
        data[mechanic] = []
        for element in gameIDList:
            rows = df.loc[df['gameID'] == element]
            found = False
            for index, row in rows.iterrows():
                if row["mechanic"] == mechanic:
                    found = True
            if found:
                data[mechanic].append(1)
            else:
                data[mechanic].append(0)
        print("done on mech ",mechanic)
    mechanicDF = pd.DataFrame(data)
    return reformated.join(mechanicDF)

def JoinMehcanics(newName, listOfNames, dataframe):
    newOperator = pd.Series([0]*len(dataframe.index))
    for name in listOfNames:
        newOperator = newOperator | dataframe[name]
        dataframe=dataframe.drop(columns=[name])
    dataframe[newName] = newOperator
    return dataframe

def FilterRankData(dataFrame):
    #remove all subtyperanks nan so we can filer by them
    #filterDF = dataFrame[dataFrame['subtype_rank'].notna()]
    blacklistDF = dataFrame.query("subtype_rank != 'Not Ranked'")

    #Fill nan in average so we can filter 0s
    blacklistDF["bayesaverage"] =blacklistDF["bayesaverage"].fillna(0)
    blacklistDF = blacklistDF.query("bayesaverage != 0.0")

    whiteListedIDS=blacklistDF["gameID"].unique()
    filteredDF = dataFrame.loc[dataFrame['gameID'].isin(whiteListedIDS)]
    # for gameID in blacklistedGameIDs:
    #     filteredDF = filteredDF.loc[not filteredDF['gameID'].isin(gameID)]
    return filteredDF

def FilterImplementationData(filteredDF,gameIDList,counter):
    implList = filteredDF.groupby("gameID")["implementation"].apply(list).reset_index(name='impls')
    #counter = 0
    # gameIDList=filteredDF["gameID"].unique()
    # filter through implementations
    solvedGameID = []
    for gameID in gameIDList:
        implementations = implList.loc[implList['gameID'] == gameIDList[counter]]
        if (not solvedGameID.__contains__(gameID)) and (not implementations.empty):
            cleaned = [x for x in implementations.iloc[0]["impls"] if str(x) != 'nan']
            listOfGameIDS = [gameIDList[counter]]
            solvedGameID.append(gameIDList[counter])
            for name in cleaned:
                foundGames = filteredDF.loc[filteredDF['name'] == name]
                if not foundGames.empty:
                    newID = foundGames.iloc[0]["gameID"]
                    listOfGameIDS.append(newID)
                    solvedGameID.append(newID)
            filteredDF = HandleReimplementations(filteredDF, listOfGameIDS)
        # else:
        #     print("already done this! ",gameID)
        if counter >= len(gameIDList)-1:
            filteredDF.to_csv("RawData/ReformattedData_filterTest_" + str(counter) + "_v2.csv")
            break
        counter = counter+1
        if counter%1000==0:
            filteredDF.to_csv("RawData/ReformattedData_filterTest_"+str(counter)+"_v2.csv")
            print("created save point: ", counter)

        #print("finished gameID : ", gameID)

    return filteredDF

def HandleReimplementations(rankedDF, listOfGameIDS):
    mechList = rankedDF.groupby("gameID")["mechanic"].apply(list).reset_index(name='mechs')
    thisMechs ={}
    for gameID in listOfGameIDS:
        mechanics = mechList.loc[mechList['gameID'] == gameID]
        cleaned = [x for x in mechanics if str(x) != 'nan']
        thisMechs[gameID] = cleaned

    equal=[]
    for gameID in listOfGameIDS:
        if gameID == listOfGameIDS[0]:
            continue
        if thisMechs[gameID].sort() == thisMechs[listOfGameIDS[0]].sort():
            equal.append(gameID)
    #do some magic if they found equal games
    mainGame = pd.Series()
    if len(equal)>0:
        # print("IVE found some equals! they are:", equal)
        avgRatingList =[]
        baeysianRatingList =[]
        stdRatingList =[]
        voteCountList=[]
        yearList=[]
        equal.append(listOfGameIDS[0])
        for gameID in equal:
            selected = rankedDF.loc[rankedDF['gameID'] == gameID]
            avgRatingList.append(selected.iloc[0]["average"])
            baeysianRatingList.append(selected.iloc[0]["bayesaverage"])
            stdRatingList.append(selected.iloc[0]["stddev"])
            voteCountList.append(selected.iloc[0]["usersrated"])
            yearList.append(selected.iloc[0]["yearpublished"])
        #define the older year to be the entry and delete all "tied" games
        olderYear = min(yearList)
        olderGameID = equal[yearList.index(olderYear)]
        mainGame = rankedDF.loc[rankedDF['gameID'] == olderGameID]
        mainGame = mainGame.iloc[0]
        #Also remove the original
        for gameID in equal:
            rankedDF = rankedDF[~((rankedDF["gameID"] == gameID) & (~rankedDF["name"].isna()))]
        #and do some math see combine averages and stdeviation
        mainGame["average"] = weightedAverage(voteCountList,avgRatingList)
        mainGame["bayesaverage"] = weightedAverage(voteCountList, baeysianRatingList)
        mainGame["stddev"] =mixStddev(voteCountList,stdRatingList)
        mainGame["usersrated"] =sum(voteCountList)
        #add line to dataframe
    if not mainGame.empty:
        rankedDF = rankedDF[~((rankedDF["gameID"] == olderGameID) & (~rankedDF["name"].isna()))]
        newDataFrame=pd.concat([rankedDF,mainGame.to_frame().T])
    else:
        newDataFrame = rankedDF
    return newDataFrame

def weightedAverage(weights,averages):
    total = 0
    for i in range(len(averages)):
        total = total + averages[i]*weights[i]
    return total/(sum(weights))

def mixStddev(sameplsizes,stddevs):
    total = 0
    for i in range(len(stddevs)):
        total = total + (stddevs[i]**2)/sameplsizes[i]
    return math.sqrt(total)

def FilterByNumRating(dataframe,threshold):
    dataframe = dataframe.query("usersrated >="+str(threshold))
    return dataframe