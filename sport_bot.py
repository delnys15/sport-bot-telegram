import logging
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

TELEGRAM_TOKEN = "8629502116:AAG_9d94MBeNorpePL-5LyoODM44SCdxLqY"
FOOTBALL_DATA_KEY = "98528561939c4b52a38521f7d25f5d65"
ODDS_API_KEY = "c8603e50da9af04d69bf1751bb2c26d4"

CHAMPIONNATS = {
    "premierleague": {"fd": "PL", "odds": "soccer_epl"},
    "ligue1": {"fd": "FL1", "odds": "soccer_france_ligue_one"},
    "bundesliga": {"fd": "BL1", "odds": "soccer_germany_bundesliga"},
    "seriea": {"fd": "SA", "odds": "soccer_italy_serie_a"},
    "laliga": {"fd": "PD", "odds": "soccer_spain_la_liga"},
    "eredivisie": {"fd": "DED", "odds": "soccer_netherlands_eredivisie"},
    "championsleague": {"fd": "CL", "odds": "soccer_uefa_champs_league"},
}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)def get_equipe_stats(equipe_nom, championnat_code):
    try:
        headers = {"X-Auth-Token": FOOTBALL_DATA_KEY}
        url = "https://api.football-data.org/v4/competitions/" + championnat_code + "/standings"
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            return {}
        data = response.json()
        standings = data.get("standings", [{}])[0].get("table", [])
        for team in standings:
            nom = team.get("team", {}).get("name", "").lower()
            if equipe_nom.lower() in nom or nom in equipe_nom.lower():
                return {
                    "position": team.get("position", "N/A"),
                    "points": team.get("points", 0),
                    "victoires": team.get("won", 0),
                    "nuls": team.get("draw", 0),
                    "defaites": team.get("lost", 0),
                    "buts_pour": team.get("goalsFor", 0),
                    "buts_contre": team.get("goalsAgainst", 0),
                    "matchs_joues": team.get("playedGames", 0),
                }
        return {}
    except Exception as e:
        logger.error("Erreur stats: " + str(e))
        return {}

def get_cotes(equipe1, equipe2, sport_key):
    try:
        url = "https://api.the-odds-api.com/v4/sports/" + sport_key + "/odds"
        params = {
            "apiKey": ODDS_API_KEY,
            "regions": "eu",
            "markets": "h2h",
            "oddsFormat": "decimal",
        }
        response = requests.get(url, params=params, timeout=10)
        if response.status_code != 200:
            return {}
        matchs = response.json()
        for match in matchs:
            home = match.get("home_team", "").lower()
            away = match.get("away_team", "").lower()
            if equipe1.lower() in home or home in equipe1.lower():
                bookmakers = match.get("bookmakers", [])
                if bookmakers:
                    outcomes = bookmakers[0].get("markets", [{}])[0].get("outcomes", [])
                    cotes = {}
                    for outcome in outcomes:
                        cotes[outcome["name"]] = outcome["price"]
                    return cotes
        return {}
    except Exception as e:
        logger.error("Erreur cotes: " + str(e))
        return {}

def calculer_score(stats1, stats2):
    score1 = 0
    score2 = 0
    details = []
    pos1 = stats1.get("position", 99)
    pos2 = stats2.get("position", 99)
    if pos1 < pos2:
        score1 += 4
        details.append("Classement: " + str(pos1) + "e vs " + str(pos2) + "e → +4 Eq1")
    elif pos2 < pos1:
        score2 += 4
        details.append("Classement: " + str(pos1) + "e vs " + str(pos2) + "e → +4 Eq2")
    else:
        score1 += 2
        score2 += 2
    mj1 = stats1.get("matchs_joues", 1)
    mj2 = stats2.get("matchs_joues", 1)
    pct1 = stats1.get("victoires", 0) / mj1 if mj1 > 0 else 0
    pct2 = stats2.get("victoires", 0) / mj2 if mj2 > 0 else 0
    if pct1 > pct2:
        score1 += 4
        details.append("Victoires: " + str(round(pct1*100)) + "% vs " + str(round(pct2*100)) + "% → +4 Eq1")
    elif pct2 > pct1:
        score2 += 4
        details.append("Victoires: " + str(round(pct1*100)) + "% vs " + str(round(pct2*100)) + "% → +4 Eq2")
    else:
        score1 += 2
        score2 += 2
    bg1 = stats1.get("buts_pour", 0)
    bg2 = stats2.get("buts_pour", 0)
    if bg1 > bg2:
        score1 += 3
        details.append("Attaque: " + str(bg1) + " vs " + str(bg2) + " → +3 Eq1")
    elif bg2 > bg1:
        score2 += 3
        details.append("Attaque: " + str(bg1) + " vs " + str(bg2) + " → +3 Eq2")
    else:
        score1 += 1
        score2 += 1
    bc1 = stats1.get("buts_contre", 99)
    bc2 = stats2.get("buts_contre", 99)
    if bc1 < bc2:
        score1 += 3
        details.append("Defense: " + str(bc1) + " vs " + str(bc2) + " → +3 Eq1")
    elif bc2 < bc1:
        score2 += 3
        details.append("Defense: " + str(bc1) + " vs " + str(bc2) + " → +3 Eq2")
    else:
        score1 += 1
        score2 += 1
    pts1 = stats1.get("points", 0)
    pts2 = stats2.get("points", 0)
    if pts1 > pts2:
        score1 += 3
        details.append("Points: " + str(pts1) + " vs " + str(pts2) + " → +3 Eq1")
    elif pts2 > pts1:
        score2 += 3
        details.append("Points: " + str(pts1) + " vs " + str(pts2) + " → +3 Eq2")
    else:
        score1 += 1
        score2 += 1
    return score1, score2, detailsasync def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texte = "🤖 Bot Analyse Sportive IA\n\nCommande:\n/analyse [championnat] [equipe1] [equipe2]\n\nExemples:\n/analyse ligue1 PSG Monaco\n/analyse premierleague Liverpool Arsenal\n/analyse bundesliga Bayern Dortmund\n/analyse seriea Inter Juventus\n/analyse laliga Barcelona Madrid"
    await update.message.reply_text(texte)

async def analyser(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) < 3:
        await update.message.reply_text("Format: /analyse [championnat] [equipe1] [equipe2]\nExemple: /analyse ligue1 PSG Monaco")
        return
    championnat_input = args[0].lower()
    equipe1 = args[1].title()
    equipe2 = args[2].title()
    champ_info = CHAMPIONNATS.get(championnat_input)
    if not champ_info:
        await update.message.reply_text("Championnat non reconnu.\nDisponibles: premierleague, ligue1, bundesliga, seriea, laliga, eredivisie, championsleague")
        return
    msg = await update.message.reply_text("Analyse en cours... " + equipe1 + " vs " + equipe2)
    try:
        stats1 = get_equipe_stats(equipe1, champ_info["fd"])
        stats2 = get_equipe_stats(equipe2, champ_info["fd"])
        cotes = get_cotes(equipe1, equipe2, champ_info["odds"])
        score1, score2, details = calculer_score(stats1, stats2)
        gagnant = equipe1 if score1 > score2 else equipe2
        diff = abs(score1 - score2)
        if diff >= 8:
            conseil = "PARI FORT : " + gagnant
            niveau = "TRES ELEVE"
        elif diff >= 5:
            conseil = "PARI RECOMMANDE : " + gagnant
            niveau = "ELEVE"
        elif diff >= 3:
            conseil = "PRUDENT : Double Chance " + gagnant
            niveau = "MOYEN"
        else:
            conseil = "MATCH EQUILIBRE - Eviter"
            niveau = "FAIBLE"
        cote_info = ""
        if cotes:
            for nom, cote in cotes.items():
                cote_info = cote_info + "\nCote " + str(nom) + ": " + str(cote)
        rapport = equipe1 + " vs " + equipe2
        rapport = rapport + "\n\nSTATS " + equipe1
        rapport = rapport + "\nPosition: " + str(stats1.get("position", "N/A"))
        rapport = rapport + "\nPoints: " + str(stats1.get("points", "N/A"))
        rapport = rapport + "\nVictoires: " + str(stats1.get("victoires", "N/A"))
        rapport = rapport + "\nButs marques: " + str(stats1.get("buts_pour", "N/A"))
        rapport = rapport + "\nButs encaisses: " + str(stats1.get("buts_contre", "N/A"))
        rapport = rapport + "\n\nSTATS " + equipe2
        rapport = rapport + "\nPosition: " + str(stats2.get("position", "N/A"))
        rapport = rapport + "\nPoints: " + str(stats2.get("points", "N/A"))
        rapport = rapport + "\nVictoires: " + str(stats2.get("victoires", "N/A"))
        rapport = rapport + "\nButs marques: " + str(stats2.get("buts_pour", "N/A"))
        rapport = rapport + "\nButs encaisses: " + str(stats2.get("buts_contre", "N/A"))
        rapport = rapport + "\n\nANALYSE IA\n"
        rapport = rapport + "\n".join(details)
        rapport = rapport + "\n\nSCORE FINAL"
        rapport = rapport + "\n" + equipe1 + ": " + str(score1) + "/20"
        rapport = rapport + "\n" + equipe2 + ": " + str(score2) + "/20"
        rapport = rapport + cote_info
        rapport = rapport + "\n\nRECOMMANDATION"
        rapport = rapport + "\n" + conseil
        rapport = rapport + "\nConfiance: " + niveau
        rapport = rapport + "\n\nPariez responsablement"
        await msg.edit_text(rapport)
    except Exception as e:
        await msg.edit_text("Erreur: " + str(e))

def main():
    print("Bot demarre!")
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("analyse", analyser))
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
