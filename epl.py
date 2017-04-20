#!/usr/bin/python

# import modules used here -- sys is a very standard one
import sys
import csv
import pdb
import requests
import json
import pandas as pd
from operator import itemgetter

# API end points
API_FOOTBALL_BASEURI = 'http://api.football-data.org'
API_FOOTBALL_FIXTURES = '/v1/competitions/426/fixtures' 
API_FOOTBALL_TEAMS = '/v1/competitions/426/teams'
API_FOOTBALL_LEAGUETABLE = '/v1/competitions/426/leagueTable'

# api token
if (len(sys.argv) < 3):
  sys.exit("error. usage: python epl.py <api_token> <team_code>")
headers = {'X-Auth-Token': 'a862d7972cf746fa830e731de124612d'}

# constants
TOTAL_MATCHDAYS = 38

# input team details
myteam = {}

def printPrettyLine():
  print "---------------------"

def getValueFromKey(arr, val_lookup, key_lookup, keys_return):
  for item in arr:
    if (item[key_lookup] == val_lookup):
      return [item[key] for key in keys_return]
  return []

def findRelevantTeams(standings, teams, teamNames):
  rel_teams = []
  for name_i in teamNames:
    (playedGames_i, points_i, position_i) = getValueFromKey(standings, name_i, \
                                                              'teamName', ['playedGames', 'points', 'position'])
    (squadMktVal_i) = getValueFromKey(teams, name_i, 'name', ['squadMarketValue'])

    if ( (myteam['points'] < (TOTAL_MATCHDAYS - playedGames_i)*3 + points_i) ):
    # and \
    #      myteam['name'] != name_i ):
      rel_teams.append({'curr_pos':position_i, 'points':points_i, 'remGames': (38-playedGames_i), \
                        'squadMktVal':squadMktVal_i, 'name':name_i})
  rel_teams = sorted(rel_teams, key=itemgetter('curr_pos'))
  print rel_teams
  return rel_teams

def printResult(where, winning_team, losing_team):
  print where + ": " + winning_team + " beats " + losing_team

def findExpectedPoints_RankBased(team_list, fixtures):
  print myteam
  res = team_list
  names = [item['name'] for item in res]
  
  for team in res:
    team['ePts_rank'] = team['points']
  
  fixtures = sorted(fixtures, key=itemgetter('status'), reverse=True)
  for fx in fixtures:
      
    if (fx['status'] == 'FINISHED'):
      continue
    
    for team in res:
      if (team['name'] == fx['homeTeamName']):
        if (fx['awayTeamName'] in names):
          if(team['curr_pos'] < (res[names.index(fx['awayTeamName'])]['curr_pos'] if fx['awayTeamName'] in names else 100)):
            team['ePts_rank'] += 3
            #printResult('HOME', team['name'], fx['awayTeamName'])
        else:
          team['ePts_rank'] += 3
          #printResult('HOME', team['name'], fx['awayTeamName'])

      if (team['name'] == fx['awayTeamName']):
        if (fx['homeTeamName'] in names):
          if(team['curr_pos'] < (res[names.index(fx['homeTeamName'])]['curr_pos'] if fx['homeTeamName'] in names else 100)):
            team['ePts_rank'] += 3
            #printResult('AWAY', team['name'], fx['homeTeamName'])
        else:
          team['ePts_rank'] += 3
          #printResult('AWAY', team['name'], fx['homeTeamName'])
  return res  

def findExpectedPoints_squadMktVal(team_list, fixtures, teams):
  #print myteam
  res = team_list
  names = [item['name'] for item in res]
  
  for team in res:
    team['ePts_mktval'] = team['points']
  
  fixtures = sorted(fixtures, key=itemgetter('status'), reverse=True)
  for fx in fixtures:
  
    if (fx['status'] == 'FINISHED'):
      continue
    
    for team in res:

      if (team['name'] == fx['homeTeamName'] or team['name'] == fx['awayTeamName']):
        if (  (getValueFromKey(teams, fx['homeTeamName'], 'name', ['squadMarketValue']) >= \
               getValueFromKey(teams, fx['awayTeamName'], 'name', ['squadMarketValue'])
              ) and 
              ( team['name'] == fx['homeTeamName'] )
           ):
          team['ePts_mktval'] += 3
          #printResult('HOME', team['name'], fx['awayTeamName'])
          
        if (  (getValueFromKey(teams, fx['homeTeamName'], 'name', ['squadMarketValue']) < \
               getValueFromKey(teams, fx['awayTeamName'], 'name', ['squadMarketValue'])
              ) and 
              ( team['name'] == fx['awayTeamName'] )
           ):
          team['ePts_mktval'] += 3
          #printResult('AWAY', team['name'], fx['homeTeamName'])
  return res

def main():
  # get input team details
  myteam['code'] = sys.argv[2]
  r = requests.get(API_FOOTBALL_BASEURI + API_FOOTBALL_TEAMS, headers=headers)
  jsonTeams = json.loads(r.text)
  if (len(getValueFromKey(jsonTeams['teams'], myteam['code'], 'code', ['name'])) == 0):
    sys.exit("err:team not found")
  print API_FOOTBALL_TEAMS, jsonTeams['teams'][0].keys()
  
  (myteam['name'], myteam['shortname']) = getValueFromKey(jsonTeams['teams'], myteam['code'], 'code', ['name', 'shortName'])
  teamNames = [str(item['name']) for item in jsonTeams['teams']]
  
  # get fixtures
  r = requests.get(API_FOOTBALL_BASEURI + API_FOOTBALL_FIXTURES, headers=headers)
  jsonFixtures = json.loads(r.text)
  #print API_FOOTBALL_FIXTURES + " keys: ", jsonFixtures['fixtures'][0].keys()
  
  # get current standings
  r = requests.get(API_FOOTBALL_BASEURI + API_FOOTBALL_LEAGUETABLE, headers=headers)
  jsonStandings = json.loads(r.text)
  (myteam['points'], myteam['curr_pos']) = getValueFromKey(jsonStandings['standing'], myteam['name'], 'teamName', ['points', 'position'])
  print myteam['code'] + " team exists.\n" + "current position, points, team name: ", myteam['curr_pos'], myteam['points'], myteam['name']
  #print API_FOOTBALL_LEAGUETABLE + " keys: ", jsonStandings['standing'][0].keys()
  
  # To get min_position in table, find teams that can actually usurp team of interest
  # Note that this might be worse than actual minimum position due to exact fixtures
  rel_teams = findRelevantTeams(jsonStandings['standing'], jsonTeams['teams'], teamNames)
  min_position = len(rel_teams)
  print myteam['name'] + " aboslute min finishing position: ", min_position, "\n"
  
  # Total points if fixtures play out per current position
  rel_teams = findExpectedPoints_RankBased(rel_teams, jsonFixtures['fixtures'])
  
  # Total points if team with the stronger home/away record wins
  
  # Total points if team with higher market value wins
  rel_teams = findExpectedPoints_squadMktVal(rel_teams, jsonFixtures['fixtures'], jsonTeams['teams'])
  print sorted(rel_teams, key=itemgetter('ePts_mktval'), reverse=True)
  
  
  
  #  for team in res:
  #    if (team['name'] == fx['homeTeamName']):
  #      if (bool(fx['odds'])):
  #        odds_yes.append(fx)
  #        a = 1.0/fx['odds']['homeWin'] + 1.0/fx['odds']['draw'] + 1.0/fx['odds']['awayWin']
  #        team['ePts_odds_based'] += (1.0/a) * (3.0/fx['odds']['homeWin'] + 1.0/fx['odds']['draw'])
  #      else:
  #        odds_no.append(fx)
  #
  #    if (team['name'] == fx['awayTeamName']):
  #      if (bool(fx['odds'])):
  #        odds_yes.append(fx)
  #        a = 1.0/fx['odds']['homeWin'] + 1.0/fx['odds']['draw'] + 1.0/fx['odds']['awayWin']
  #        team['ePts_odds_based'] += (1.0/a) * (3.0/fx['odds']['awayWin'] + 1.0/fx['odds']['draw'])
  #      else:
  #        odds_no.append(fx)


  
  
# Standard boilerplate to call the main() function to begin
# the program.
if __name__ == '__main__':
  main()