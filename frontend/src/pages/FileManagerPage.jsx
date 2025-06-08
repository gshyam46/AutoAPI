import { useState, useEffect } from "react";
import { FileList } from "../components/FileManager/FileList";
import { FileDetails } from "../components/FileManager/FileDetails";
import { APIConfig } from "../components/FileManager/APIConfig";
import { Alert, AlertDescription } from "../components/ui/alert";
import { AlertCircle } from "lucide-react";

function FileManagerPage() {
  const [files, setFiles] = useState([]);
  const [selectedFile, setSelectedFile] = useState(null);
  const [selectedSheet, setSelectedSheet] = useState("");
  const [selectedColumns, setSelectedColumns] = useState([]);
  const [endpointPath, setEndpointPath] = useState("");
  const [method, setMethod] = useState("GET");
  const [filterCol, setFilterCol] = useState("");
  const [filterOp, setFilterOp] = useState(">");
  const [filterVal, setFilterVal] = useState("");
  const [aggCol, setAggCol] = useState("");
  const [aggFunc, setAggFunc] = useState("avg");
  const [groupBy, setGroupBy] = useState("");
  const [apiConfigs, setApiConfigs] = useState([]);
  const [error, setError] = useState("");

  const fetchFiles = async () => {
    try {
      const response = await fetch("http://localhost:8000/files");
      const data = await response.json();
      setFiles(data);
      setError("");
    } catch (error) {
      setError("Failed to fetch files");
    }
  };

  const fetchApiConfigs = async () => {
    try {
      const response = await fetch("http://localhost:8000/api-configs");
      const data = await response.json();
      setApiConfigs(data);
      setError("");
    } catch (error) {
      setError("Failed to fetch API configs");
    }
  };

  useEffect(() => {
    fetchFiles();
    fetchApiConfigs();
  }, []);

  const handleFileSelect = async (fileId) => {
    try {
      const response = await fetch(`http://localhost:8000/files/${fileId}`);
      const data = await response.json();
      setSelectedFile(data);
      setSelectedSheet(data.selected_sheet);
      setSelectedColumns(data.selected_columns);
      setError("");
    } catch (error) {
      setError("Failed to fetch file");
    }
  };

  const handleUpdateFile = async () => {
    try {
      const response = await fetch(
        `http://localhost:8000/files/${selectedFile.id}`,
        {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            selected_sheet: selectedSheet,
            selected_columns: selectedColumns,
          }),
        }
      );
      if (response.ok) {
        fetchFiles();
        const updatedFile = await response.json();
        setSelectedFile(updatedFile);
        setError("");
      } else {
        const data = await response.json();
        setError(data.detail || "Failed to update file");
      }
    } catch (error) {
      setError("Failed to update file");
    }
  };

  const handleDeleteFile = async (fileId) => {
    try {
      const response = await fetch(`http://localhost:8000/files/${fileId}`, {
        method: "DELETE",
      });
      if (response.ok) {
        fetchFiles();
        setSelectedFile(null);
        fetchApiConfigs();
        setError("");
      } else {
        const data = await response.json();
        setError(data.detail || "Failed to delete file");
      }
    } catch (error) {
      setError("Failed to delete file");
    }
  };

  const handleCreateAPI = async () => {
    if (!endpointPath || !filterCol) {
      setError("Please specify endpoint path and filter column");
      return;
    }
    const queryLogic = {
      filters: [
        {
          column: filterCol,
          operator: filterOp,
          value: parseFloat(filterVal) || filterVal,
        },
      ],
      aggregates: aggCol ? [{ column: aggCol, function: aggFunc }] : [],
      group_by: groupBy ? [groupBy] : [],
    };
    try {
      const response = await fetch("http://localhost:8000/api-configs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          file_id: selectedFile.id,
          endpoint_path: endpointPath,
          method,
          query_logic: queryLogic,
        }),
      });
      const data = await response.json();
      if (response.ok) {
        alert(`API created! Test it at http://localhost:8080${endpointPath}`);
        fetchApiConfigs();
        setEndpointPath("");
        setFilterCol("");
        setFilterOp(">");
        setFilterVal("");
        setAggCol("");
        setAggFunc("avg");
        setGroupBy("");
        setError("");
      } else {
        setError(data.detail || "Failed to create API");
      }
    } catch (error) {
      setError("Failed to create API");
    }
  };

  return (
    <div className="container mx-auto py-8 space-y-6">
      <h1 className="text-3xl font-bold tracking-tight">File Manager</h1>

      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <FileList
          files={files}
          onFileSelect={handleFileSelect}
          onFileDelete={handleDeleteFile}
        />

        {selectedFile && (
          <div className="space-y-6">
            <FileDetails
              selectedFile={selectedFile}
              selectedSheet={selectedSheet}
              selectedColumns={selectedColumns}
              onSheetChange={setSelectedSheet}
              onColumnsChange={setSelectedColumns}
              onUpdate={handleUpdateFile}
            />

            <APIConfig
              selectedFile={selectedFile}
              endpointPath={endpointPath}
              method={method}
              filterCol={filterCol}
              filterOp={filterOp}
              filterVal={filterVal}
              aggCol={aggCol}
              aggFunc={aggFunc}
              groupBy={groupBy}
              onEndpointPathChange={setEndpointPath}
              onMethodChange={setMethod}
              onFilterColChange={setFilterCol}
              onFilterOpChange={setFilterOp}
              onFilterValChange={setFilterVal}
              onAggColChange={setAggCol}
              onAggFuncChange={setAggFunc}
              onGroupByChange={setGroupBy}
              onCreateAPI={handleCreateAPI}
            />
          </div>
        )}
      </div>
    </div>
  );
}

export default FileManagerPage;
