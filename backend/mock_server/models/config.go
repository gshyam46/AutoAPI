package models

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
