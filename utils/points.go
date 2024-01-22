package utils


import (
	"fmt"
	"time"
	"container/list"
)


type point struct {
	guildID string
	channelID string
	userID string
	timestamp time.Time
	source string
}


var allPoints = make(map[string]map[string]list.List)


// Load up all of the points from the database
func GetAllPoints() map[string]map[string]list.List {
	db := GetDB()
	defer db.Close()
	rows, _ := db.Query(`
		SELECT
			guild_id::TEXT,
			channel_id::TEXT,
			user_id::TEXT,
			timestamp,
			source
		FROM
			user_points
		LIMIT 1000
		`)
	counter := 0
	for rows.Next() {
		var guildID, channelID, userID string
		var timestamp time.Time
		var source string
		rows.Scan(&guildID, &channelID, &userID, &timestamp, &source)
		p := point{guildID, channelID, userID, timestamp, source}
		arr := allPoints[p.guildID][p.userID]
		arr.PushBack(p)
		counter++
		if counter % 500_000 == 0 {
			fmt.Println("Processed", counter, time.Now())
		}
	}
	return allPoints
}


// Add a point to the database as well as to the cache
func AddPoint(guildID, channelID, userID string, timestamp time.Time, source string) {
	db := GetDB()
	defer db.Close()
	db.Exec(`
		INSERT INTO
			user_points
			(
				guild_id,
				channel_id,
				user_id,
				timestamp,
				source
			)
		VALUES ($1::BIGINT, $2::BIGINT, $3::BIGINT, $4, $5)`,
		guildID, channelID, userID, timestamp, source,
	)
	p := point{guildID, channelID, userID, timestamp, source}
	arr := allPoints[p.guildID][p.userID]
	arr.PushBack(p)
	fmt.Println("Added point", p)
}
