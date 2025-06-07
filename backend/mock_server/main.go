package main

import (
	"bytes"
	"encoding/json"
	"log"
	"net/http"
	"sync"
	"time"

	"github.com/gin-gonic/gin"
)

type APIConfig struct {
	ID           int                    `json:"id"`
	FileID       int                    `json:"file_id"`
	EndpointPath string                 `json:"endpoint_path"`
	Method       string                 `json:"method"`
	QueryLogic   map[string]interface{} `json:"query_logic"`
}

var (
	configs []APIConfig
	mu      sync.RWMutex
)

func fetchAPIConfigs() {
	resp, err := http.Get("http://localhost:8000/api-configs")
	if err != nil {
		log.Println("Failed to fetch configs:", err)
		return
	}
	defer resp.Body.Close()
	var newConfigs []APIConfig
	if err := json.NewDecoder(resp.Body).Decode(&newConfigs); err != nil {
		log.Println("Failed to decode configs:", err)
		return
	}
	mu.Lock()
	configs = newConfigs
	mu.Unlock()
}

func executeQuery(fileID int, queryLogic map[string]interface{}) (interface{}, error) {
	payload := map[string]interface{}{
		"file_id":     fileID,
		"sheet_name":  nil,
		"query_logic": queryLogic,
	}
	body, _ := json.Marshal(payload)
	resp, err := http.Post("http://localhost:8000/query", "application/json", bytes.NewBuffer(body))
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	var result interface{}
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, err
	}
	return result, nil
}

func main() {
	r := gin.Default()

	r.GET("/health", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{"status": "healthy"})
	})

	go func() {
		for {
			fetchAPIConfigs()
			mu.RLock()
			for _, config := range configs {
				cfg := config // Capture loop variable
				switch cfg.Method {
				case "GET":
					r.GET(cfg.EndpointPath, func(c *gin.Context) {
						result, err := executeQuery(cfg.FileID, cfg.QueryLogic)
						if err != nil {
							c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
							return
						}
						c.JSON(http.StatusOK, result)
					})
				case "POST":
					r.POST(cfg.EndpointPath, func(c *gin.Context) {
						result, err := executeQuery(cfg.FileID, cfg.QueryLogic)
						if err != nil {
							c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
							return
						}
						c.JSON(http.StatusOK, result)
					})
				}
			}
			mu.RUnlock()
			time.Sleep(10 * time.Second)
		}
	}()

	r.Run(":8080")
}
