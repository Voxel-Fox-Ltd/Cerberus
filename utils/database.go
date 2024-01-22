package utils


import (
	"os"

	"database/sql"
	_ "github.com/lib/pq"

	dotenv "github.com/joho/godotenv"
)


// Get an open datbase connection
func GetDB() *sql.DB {
	_ = dotenv.Load()
	db, _ := sql.Open("postgres", os.Getenv("DSN"))
	return db
}
