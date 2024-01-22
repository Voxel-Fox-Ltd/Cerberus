package events


import (
	"time"

    "github.com/bwmarrin/discordgo"

    "Cerberus/utils"
)


var lastMessage = make(map[string]map[string]time.Time)
var oneMinute, _ = time.ParseDuration("1m")


func MessageHandler(session *discordgo.Session, message *discordgo.MessageCreate) {

	// Ignore DMs
	if message.GuildID == "" {
		return
	}

	// Check user's last message timestamp
	lastMessageStamp, ok := lastMessage[message.GuildID][message.Author.ID]
	if ok && lastMessageStamp.Add(oneMinute).Unix() > time.Now().Unix() {
		return
	}

	// Add point to db and store new time
	t := time.Now()
	gm := lastMessage[message.GuildID]
	if gm == nil {
		lastMessage[message.GuildID] = make(map[string]time.Time)
	}
	lastMessage[message.GuildID][message.Author.ID] = t
	utils.AddPoint(message.GuildID, message.ChannelID, message.Author.ID, t, "message")
}
