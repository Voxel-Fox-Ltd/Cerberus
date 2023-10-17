package Handler

import (
	"Cerberus/Logging"
	"Cerberus/Temp"
	"fmt"

	"github.com/bwmarrin/discordgo"
)

// I'm testing maps in Golang THIS CODE MUST BE REMOVED
func OnMessageCreate(session *discordgo.Session, message *discordgo.MessageCreate){
	if message.Author.ID != session.State.User.ID{
		Logging.Log(Logging.LogMessage{message.Author.Username+" count "+fmt.Sprint(Temp.UserDataMap[message.Author.ID]),Logging.Verbose});
		Temp.UserDataMap[message.Author.ID]+=1;
		session.ChannelMessageSend(message.ChannelID,fmt.Sprintf("%s has sent %d message(s)",message.Author.Username,Temp.UserDataMap[message.Author.ID]));
	}
}