package main

/*
	- STRUCTURE -
	I've specifically made functions such as OnStart(), OnShutdown(), and OnDiscord() that are ran in main()
	So we wouldn't have to read unnecesarry code. Also looks very tidy :)

	- CASES -
	when to use:
	camelCase  = if a variable is inside a function, arguments, 
	PascalCase = Function Names, Structs, Types, Folders, .go Files, Package Names,
	snake_case = never :) (lmk if you can find a use for it)
*/


import (
	// Local packages
	"Cerberus/Handler"
	"Cerberus/Logging"

	// System packages 
	"os"
	"os/signal"
	"syscall"

	// 3rd party packages
	"github.com/bwmarrin/discordgo"
)

/// Work here please
func OnDiscord(discord *discordgo.Session){
	discord.Identify.Intents = discordgo.IntentsGuildMessages;

	// Handlers
	discord.AddHandler(Handler.OnMessageCreate)
}

// If something needs to run before discord connection
// It goes here
func OnStart(){
	// Advising to keep this as first function
	Logging.LogInit();
}

// Anything that needs to be shutdown goes here
func OnShutdown(){

	// Advising to keep this as last function
	Logging.LogClose();
}

func GetAPIKey() string{
	k, err := os.ReadFile("config/DiscordKey");
	Handler.CheckError(err,
		Logging.LogMessage{"Read the Discord Key",Logging.Verbose},
		Logging.LogMessage{"Failed to read Discord Key",Logging.Critical});
	return string(k);
}


// You shouldn't have to change anything here
func main(){
	OnStart();

	// Boilerplate discord api code
	discord, err := discordgo.New("Bot "+GetAPIKey());
	Handler.CheckError(err,
		Logging.LogMessage{"Created Discord session",Logging.Info},
		Logging.LogMessage{"Failed creating Discord session",Logging.Critical});

	OnDiscord(discord);

	err = discord.Open()
	Handler.CheckError(err,
		Logging.LogMessage{"Connecting to Discord as \""+discord.State.User.Username+"\"",Logging.Info},
		Logging.LogMessage{"Failed to connect to Discord!",Logging.Critical});

	Logging.LogToConsole(Logging.LogMessage{"Bot is online! You can shutdown the bot by pressing CTRL-C",Logging.Info});
	
	// Hang state
	live := make(chan os.Signal,1);
	signal.Notify(live,syscall.SIGINT,syscall.SIGTERM);
	<-live
	
	// Closing sequence
	OnShutdown();
	Logging.Log(Logging.LogMessage{"Shutting down the bot!",Logging.Warning});
	discord.Close();
}