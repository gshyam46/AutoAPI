package main

import (
	"github.com/gshyam46/AutoAPI/backend/mock_server/services"

	"github.com/gin-gonic/gin"
)

func main() {
	r := gin.Default()

	// Register health endpoint
	r.GET("/health", func(c *gin.Context) {
		c.JSON(200, gin.H{"status": "healthy"})
	})

	// Start background config fetcher and dynamic route registration
	go services.StartConfigFetcher(r)

	// Run the server
	r.Run(":8080")
}
