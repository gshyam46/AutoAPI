package query

import (
	"database/sql"
	"fmt"
	"path/filepath"
	"strings"

	_ "github.com/mattn/go-sqlite3"
)

func ExecuteQuery(fileID string, operation string, queryLogic map[string]interface{}, payload interface{}, joinConfig *map[string]interface{}) (interface{}, error) {
	dbPath := filepath.Join("data", fmt.Sprintf("%s.db", fileID))
	db, err := sql.Open("sqlite3", dbPath)
	if err != nil {
		return nil, fmt.Errorf("error opening database: %v", err)
	}
	defer db.Close()

	switch operation {
	case "select":
		return executeSelect(db, queryLogic, joinConfig)
	case "insert":
		return executeInsert(db, payload)
	case "update":
		return executeUpdate(db, queryLogic, payload)
	case "delete":
		return executeDelete(db, queryLogic)
	default:
		return nil, fmt.Errorf("unsupported operation: %s", operation)
	}
}

func executeSelect(db *sql.DB, queryLogic map[string]interface{}, joinConfig *map[string]interface{}) (interface{}, error) {
	tableName, ok := queryLogic["table"].(string)
	if !ok {
		return nil, fmt.Errorf("table name not specified in query logic")
	}

	query := fmt.Sprintf("SELECT * FROM %s", tableName)
	args := []interface{}{}

	if conditions, ok := queryLogic["conditions"].(map[string]interface{}); ok {
		whereClauses := []string{}
		for field, value := range conditions {
			whereClauses = append(whereClauses, fmt.Sprintf("%s = ?", field))
			args = append(args, value)
		}
		if len(whereClauses) > 0 {
			query += " WHERE " + strings.Join(whereClauses, " AND ")
		}
	}

	if joinConfig != nil {
		joinTable, ok := (*joinConfig)["table"].(string)
		if !ok {
			return nil, fmt.Errorf("join table not specified")
		}
		joinField, ok := (*joinConfig)["field"].(string)
		if !ok {
			return nil, fmt.Errorf("join field not specified")
		}
		query += fmt.Sprintf(" JOIN %s ON %s.%s = %s.%s", joinTable, tableName, joinField, joinTable, joinField)
	}

	rows, err := db.Query(query, args...)
	if err != nil {
		return nil, fmt.Errorf("error executing query: %v", err)
	}
	defer rows.Close()

	columns, err := rows.Columns()
	if err != nil {
		return nil, fmt.Errorf("error getting columns: %v", err)
	}

	var result []map[string]interface{}
	for rows.Next() {
		values := make([]interface{}, len(columns))
		valuePtrs := make([]interface{}, len(columns))
		for i := range columns {
			valuePtrs[i] = &values[i]
		}

		if err := rows.Scan(valuePtrs...); err != nil {
			return nil, fmt.Errorf("error scanning row: %v", err)
		}

		row := make(map[string]interface{})
		for i, col := range columns {
			val := values[i]
			switch v := val.(type) {
			case []byte:
				row[col] = string(v)
			default:
				row[col] = v
			}
		}
		result = append(result, row)
	}

	return result, nil
}

func executeInsert(db *sql.DB, payload interface{}) (interface{}, error) {
	data, ok := payload.(map[string]interface{})
	if !ok {
		return nil, fmt.Errorf("invalid payload format")
	}

	tableName, ok := data["table"].(string)
	if !ok {
		return nil, fmt.Errorf("table name not specified in payload")
	}

	fields := []string{}
	placeholders := []string{}
	values := []interface{}{}

	for field, value := range data {
		if field != "table" {
			fields = append(fields, field)
			placeholders = append(placeholders, "?")
			values = append(values, value)
		}
	}

	query := fmt.Sprintf("INSERT INTO %s (%s) VALUES (%s)",
		tableName,
		strings.Join(fields, ", "),
		strings.Join(placeholders, ", "))

	result, err := db.Exec(query, values...)
	if err != nil {
		return nil, fmt.Errorf("error executing insert: %v", err)
	}

	id, err := result.LastInsertId()
	if err != nil {
		return nil, fmt.Errorf("error getting last insert ID: %v", err)
	}

	return map[string]interface{}{
		"id":      id,
		"message": "Record inserted successfully",
	}, nil
}

func executeUpdate(db *sql.DB, queryLogic map[string]interface{}, payload interface{}) (interface{}, error) {
	tableName, ok := queryLogic["table"].(string)
	if !ok {
		return nil, fmt.Errorf("table name not specified in query logic")
	}

	data, ok := payload.(map[string]interface{})
	if !ok {
		return nil, fmt.Errorf("invalid payload format")
	}

	setClauses := []string{}
	values := []interface{}{}

	for field, value := range data {
		if field != "table" {
			setClauses = append(setClauses, fmt.Sprintf("%s = ?", field))
			values = append(values, value)
		}
	}

	query := fmt.Sprintf("UPDATE %s SET %s", tableName, strings.Join(setClauses, ", "))

	if conditions, ok := queryLogic["conditions"].(map[string]interface{}); ok {
		whereClauses := []string{}
		for field, value := range conditions {
			whereClauses = append(whereClauses, fmt.Sprintf("%s = ?", field))
			values = append(values, value)
		}
		if len(whereClauses) > 0 {
			query += " WHERE " + strings.Join(whereClauses, " AND ")
		}
	}

	result, err := db.Exec(query, values...)
	if err != nil {
		return nil, fmt.Errorf("error executing update: %v", err)
	}

	rowsAffected, err := result.RowsAffected()
	if err != nil {
		return nil, fmt.Errorf("error getting rows affected: %v", err)
	}

	return map[string]interface{}{
		"rows_affected": rowsAffected,
		"message":       "Records updated successfully",
	}, nil
}

func executeDelete(db *sql.DB, queryLogic map[string]interface{}) (interface{}, error) {
	tableName, ok := queryLogic["table"].(string)
	if !ok {
		return nil, fmt.Errorf("table name not specified in query logic")
	}

	query := fmt.Sprintf("DELETE FROM %s", tableName)
	args := []interface{}{}

	if conditions, ok := queryLogic["conditions"].(map[string]interface{}); ok {
		whereClauses := []string{}
		for field, value := range conditions {
			whereClauses = append(whereClauses, fmt.Sprintf("%s = ?", field))
			args = append(args, value)
		}
		if len(whereClauses) > 0 {
			query += " WHERE " + strings.Join(whereClauses, " AND ")
		}
	}

	result, err := db.Exec(query, args...)
	if err != nil {
		return nil, fmt.Errorf("error executing delete: %v", err)
	}

	rowsAffected, err := result.RowsAffected()
	if err != nil {
		return nil, fmt.Errorf("error getting rows affected: %v", err)
	}

	return map[string]interface{}{
		"rows_affected": rowsAffected,
		"message":       "Records deleted successfully",
	}, nil
}
