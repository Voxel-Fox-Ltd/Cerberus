package commands

import (
	"github.com/FedorLap2006/disgolf"
	"github.com/bwmarrin/discordgo"

	"Cerberus/utils"
)


type PointsModule struct{}


func (m PointsModule) Ping(ctx *disgolf.Ctx) {
	_ = ctx.Respond(&discordgo.InteractionResponse{
		Type: discordgo.InteractionResponseChannelMessageWithSource,
		Data: &discordgo.InteractionResponseData{
			Content: fmt.Sprintf(
				":ping_pong: %v",
				ctx.HeartbeatLatency(),
			),
		},
	})
}


func (m PointsModule) Commands() []*disgolf.Command {
	return []*disgolf.Command{
		{
			Name:           "ping",
			Description:    "Get bot ping",
			Handler:        disgolf.HandlerFunc(m.Ping),
		},
	}
}
