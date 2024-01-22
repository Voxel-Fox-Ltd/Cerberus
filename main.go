package main


import (
    "fmt"
    "log"
    "os"
    "os/signal"
    "syscall"

    "github.com/FedorLap2006/disgolf"
    "github.com/bwmarrin/discordgo"
    dotenv "github.com/joho/godotenv"

    "Cerberus/utils"
    "Cerberus/events"
)


func init() {
    err := dotenv.Load()
    if err != nil {
        log.Fatal(fmt.Errorf("cannot load .env: %w", err))
    }
}


var modules = []interface{ Commands() []*disgolf.Command }{
    // ExampleModule{},
}


func loadModules(bot *disgolf.Bot) {
    for _, m := range modules {
        for _, command := range m.Commands() {
            bot.Router.Register(command)
        }
    }
}


func main() {

    // Make a new bot
    bot, err := disgolf.New(os.Getenv("TOKEN"))
    if err != nil {
        log.Fatal(fmt.Errorf("failed to initialise session: %w", err))
    }

    // Load our commands
    loadModules(bot)

    // Add our message handler
    bot.AddHandler(bot.Router.HandleInteraction)

    // Add our ready handler
    bot.AddHandler(func(*discordgo.Session, *discordgo.Ready) { log.Println("Ready!") })
    bot.AddHandler(events.MessageHandler)

    // Get cache data
    utils.GetAllPoints()

    // Create bot object and websocket
    err = bot.Open()
    if err != nil {
        log.Fatal(fmt.Errorf("failed to open session: %w", err))
    }
    // err = bot.Router.Sync(bot.Session, "", os.Getenv("TEST_GUILD_ID"))
    // if err != nil {
    //     log.Fatal(fmt.Errorf("failed to sync commands: %w", err))
    // }

    // Wait until close
    ech := make(chan os.Signal)
    signal.Notify(ech, os.Kill, syscall.SIGTERM)
    <-ech
    _ = bot.Close()
}
