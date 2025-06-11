package routes

import (
	"fmt"
	"strconv"

	"github.com/gin-gonic/gin"
	"github.com/gshyam46/AutoAPI/backend/mock_server/models"
	"github.com/gshyam46/AutoAPI/backend/mock_server/query"
)

func RegisterDynamicRoute(r *gin.Engine, config models.UserConfig, registeredRoutes map[string]bool) {
	routeKey := fmt.Sprintf("%s:%s", config.Method, config.EndpointPath)
	if registeredRoutes[routeKey] {
		return
	}

	fileID := strconv.Itoa(config.FileID)

	switch config.Method {
	case "GET":
		r.GET(config.EndpointPath, func(c *gin.Context) {
			var joinConfig *map[string]interface{}
			if config.QueryLogic["join_config"] != nil {
				jc, ok := config.QueryLogic["join_config"].(map[string]interface{})
				if ok {
					joinConfig = &jc
				}
			}
			result, err := query.ExecuteQuery(fileID, "select", config.QueryLogic, nil, joinConfig)
			if err != nil {
				c.JSON(500, gin.H{"error": err.Error()})
				return
			}
			c.JSON(200, result)
		})
	case "POST":
		r.POST(config.EndpointPath, func(c *gin.Context) {
			var payload interface{}
			if err := c.BindJSON(&payload); err != nil {
				c.JSON(400, gin.H{"error": "invalid payload"})
				return
			}
			result, err := query.ExecuteQuery(fileID, "insert", nil, payload, nil)
			if err != nil {
				c.JSON(500, gin.H{"error": err.Error()})
				return
			}
			c.JSON(200, result)
		})
	case "PUT":
		r.PUT(config.EndpointPath, func(c *gin.Context) {
			var payload interface{}
			if err := c.BindJSON(&payload); err != nil {
				c.JSON(400, gin.H{"error": "invalid payload"})
				return
			}
			result, err := query.ExecuteQuery(fileID, "update", config.QueryLogic, payload, nil)
			if err != nil {
				c.JSON(500, gin.H{"error": err.Error()})
				return
			}
			c.JSON(200, result)
		})
	case "DELETE":
		r.DELETE(config.EndpointPath, func(c *gin.Context) {
			result, err := query.ExecuteQuery(fileID, "delete", config.QueryLogic, nil, nil)
			if err != nil {
				c.JSON(500, gin.H{"error": err.Error()})
				return
			}
			c.JSON(200, result)
		})
	}
	registeredRoutes[routeKey] = true
}

func UpdateRouter(oldRouter, newRouter *gin.Engine) {
	*oldRouter = *newRouter
}
