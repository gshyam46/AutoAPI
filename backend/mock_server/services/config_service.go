package services

import (
	"log"
	"sync"
	"time"

	"github.com/gshyam46/AutoAPI/backend/mock_server/models"
	"github.com/gshyam46/AutoAPI/backend/mock_server/routes"
	"github.com/gshyam46/AutoAPI/backend/mock_server/utils"

	"github.com/gin-gonic/gin"
)

var (
	configs          []models.UserConfig
	mu               sync.RWMutex
	registeredRoutes map[string]bool
)

func init() {
	registeredRoutes = make(map[string]bool)
}

func FetchAPIConfigs() {
	client := utils.NewHTTPClient()
	resp, err := client.Get("http://localhost:8000/api-configs")
	if err != nil {
		log.Println("Error fetching configs:", err)
		return
	}
	defer resp.Body.Close()

	if resp.StatusCode != 200 {
		log.Printf("Non-200 status code: %d", resp.StatusCode)
		return
	}

	var newConfigs []models.UserConfig
	if err := utils.DecodeJSON(resp.Body, &newConfigs); err != nil {
		log.Println("Error decoding JSON:", err)
		return
	}

	mu.Lock()
	configs = newConfigs
	mu.Unlock()
}

func StartConfigFetcher(r *gin.Engine) {
	for {
		FetchAPIConfigs()
		mu.RLock()
		newRouter := gin.New()
		newRouter.GET("/health", func(c *gin.Context) {
			c.JSON(200, gin.H{"status": "healthy"})
		})

		newRegisteredRoutes := make(map[string]bool)
		for _, config := range configs {
			routes.RegisterDynamicRoute(newRouter, config, newRegisteredRoutes)
		}

		mu.Lock()
		routes.UpdateRouter(r, newRouter)
		registeredRoutes = newRegisteredRoutes
		mu.Unlock()

		mu.RUnlock()
		time.Sleep(10 * time.Second)
	}
}

func GetConfigs() []models.UserConfig {
	mu.RLock()
	defer mu.RUnlock()
	return configs
}
