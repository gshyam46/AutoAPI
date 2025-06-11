package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"sync"
	"time"

	"github.com/gin-gonic/gin"
)

type UserConfig struct {
	ID           int                    `json:"id"`
	FileID       int                    `json:"file_id"`
	EndpointPath string                 `json:"endpoint_path"`
	Method       string                 `json:"method"`
	QueryLogic   map[string]interface{} `json:"query_logic"`
}

type QueryRequest struct {
	FileID     int                     `json:"file_id"`
	SheetName  *string                 `json:"sheet_name"`
	Operation  string                  `json:"operation"`
	QueryLogic map[string]interface{}  `json:"query_logic,omitempty"`
	Payload    interface{}             `json:"payload"`
	JoinConfig *map[string]interface{} `json:"join_config"`
}

var (
	configs          []UserConfig
	mu               sync.RWMutex
	registeredRoutes map[string]bool
)

func fetchAPIConfigs() {
	resp, err := http.Get("http://localhost:8000/api-configs")
	if err != nil {
		log.Println("Error fetching configs:", err)
		return
	}
	defer resp.Body.Close()

	if resp.StatusCode != 200 {
		log.Printf("Non-200 status code: %d", resp.StatusCode)
		return
	}

	var newConfigs []UserConfig
	if err := json.NewDecoder(resp.Body).Decode(&newConfigs); err != nil {
		log.Println("Error decoding JSON:", err)
		return
	}

	mu.Lock()
	configs = newConfigs
	mu.Unlock()
}

func executeQuery(fileID int, operation string, queryLogic map[string]interface{}, payload interface{}, joinConfig *map[string]interface{}) (interface{}, error) {
	requestBody := QueryRequest{
		FileID:     fileID,
		SheetName:  nil,
		Operation:  operation,
		Payload:    payload,
		JoinConfig: joinConfig,
	}
	if queryLogic != nil {
		requestBody.QueryLogic = queryLogic
	}
	body, err := json.Marshal(requestBody)
	if err != nil {
		return nil, err
	}
	resp, err := http.Post("http://localhost:8000/query", "application/json", bytes.NewBuffer(body))
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != 200 {
		errorBody, err := io.ReadAll(resp.Body)
		if err != nil {
			return nil, fmt.Errorf("failed to read error body: %v", err)
		}
		return nil, fmt.Errorf("query failed with status %d: %s", resp.StatusCode, string(errorBody))
	}

	var result interface{}
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, err
	}
	return result, nil
}

func main() {
	r := gin.Default()
	registeredRoutes = make(map[string]bool)

	r.GET("/health", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{"status": "healthy"})
	})

	go func() {
		for {
			fetchAPIConfigs()
			mu.RLock()
			newRouter := gin.New()
			newRouter.GET("/health", func(c *gin.Context) {
				c.JSON(http.StatusOK, gin.H{"status": "healthy"})
			})

			newRegisteredRoutes := make(map[string]bool)

			for _, config := range configs {
				cfg := config
				routeKey := fmt.Sprintf("%s:%s", cfg.Method, cfg.EndpointPath)
				if registeredRoutes[routeKey] {
					continue
				}

				switch cfg.Method {
				case "GET":
					newRouter.GET(cfg.EndpointPath, func(c *gin.Context) {
						var joinConfig *map[string]interface{}
						if cfg.QueryLogic["join_config"] != nil {
							jc, ok := cfg.QueryLogic["join_config"].(map[string]interface{})
							if ok {
								joinConfig = &jc
							}
						}
						result, err := executeQuery(cfg.FileID, "select", cfg.QueryLogic, nil, joinConfig)
						if err != nil {
							c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
							return
						}
						c.JSON(http.StatusOK, result)
					})
				case "POST":
					newRouter.POST(cfg.EndpointPath, func(c *gin.Context) {
						var payload interface{}
						if err := c.BindJSON(&payload); err != nil {
							c.JSON(http.StatusBadRequest, gin.H{"error": "invalid payload"})
							return
						}
						result, err := executeQuery(cfg.FileID, "insert", nil, payload, nil)
						if err != nil {
							c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
							return
						}
						c.JSON(http.StatusOK, result)
					})
				case "PUT":
					newRouter.PUT(cfg.EndpointPath, func(c *gin.Context) {
						var payload interface{}
						if err := c.BindJSON(&payload); err != nil {
							c.JSON(http.StatusBadRequest, gin.H{"error": "invalid payload"})
							return
						}
						result, err := executeQuery(cfg.FileID, "update", cfg.QueryLogic, payload, nil)
						if err != nil {
							c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
							return
						}
						c.JSON(http.StatusOK, result)
					})
				case "DELETE":
					newRouter.DELETE(cfg.EndpointPath, func(c *gin.Context) {
						result, err := executeQuery(cfg.FileID, "delete", cfg.QueryLogic, nil, nil)
						if err != nil {
							c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
							return
						}
						c.JSON(http.StatusOK, result)
					})
				}
				newRegisteredRoutes[routeKey] = true
			}

			mu.Lock()
			r = newRouter
			registeredRoutes = newRegisteredRoutes
			mu.Unlock()

			mu.RUnlock()
			time.Sleep(10 * time.Second)
		}
	}()

	r.Run(":8080")
}
