package services

import (
	"bytes"
	"fmt"
	"io"

	"github.com/gshyam46/AutoAPI/backend/mock_server/models"
	"github.com/gshyam46/AutoAPI/backend/mock_server/utils"
)

func ExecuteQuery(fileID int, operation string, queryLogic map[string]interface{}, payload interface{}, joinConfig *map[string]interface{}) (interface{}, error) {
	requestBody := models.QueryRequest{
		FileID:     fileID,
		SheetName:  nil,
		Operation:  operation,
		Payload:    payload,
		JoinConfig: joinConfig,
	}
	if queryLogic != nil {
		requestBody.QueryLogic = queryLogic
	}

	body, err := utils.EncodeJSON(requestBody)
	if err != nil {
		return nil, fmt.Errorf("failed to encode request body: %v", err)
	}

	client := utils.NewHTTPClient()
	resp, err := client.Post("http://localhost:8000/query", "application/json", bytes.NewBuffer(body))
	if err != nil {
		return nil, fmt.Errorf("failed to execute query: %v", err)
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
	if err := utils.DecodeJSON(resp.Body, &result); err != nil {
		return nil, fmt.Errorf("failed to decode response: %v", err)
	}
	return result, nil
}
