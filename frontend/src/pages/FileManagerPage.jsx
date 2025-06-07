import { useState, useEffect } from "react";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../components/ui/select";

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
  const [apiConfigs, setApiConfigs] = useState([]);

  const fetchFiles = async () => {
    try {
      const response = await fetch("http://localhost:8000/files");
      const data = await response.json();
      setFiles(data);
    } catch (error) {
      console.error("Failed to fetch files");
    }
  };

  const fetchApiConfigs = async () => {
    try {
      const response = await fetch("http://localhost:8000/api-configs");
      const data = await response.json();
      setApiConfigs(data);
    } catch (error) {
      console.error("Failed to fetch API configs");
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
    } catch (error) {
      console.error("Failed to fetch file");
    }
  };

  const handleUpdateFile = async () => {
    try {
      await fetch(`http://localhost:8000/files/${selectedFile.id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          selected_sheet: selectedSheet,
          selected_columns: selectedColumns,
        }),
      });
      fetchFiles();
    } catch (error) {
      console.error("Failed to update file");
    }
  };

  const handleDeleteFile = async (fileId) => {
    try {
      await fetch(`http://localhost:8000/files/${fileId}`, {
        method: "DELETE",
      });
      fetchFiles();
      setSelectedFile(null);
    } catch (error) {
      console.error("Failed to delete file");
    }
  };

  const handleCreateAPI = async () => {
    if (!endpointPath || !filterCol) {
      alert("Please specify endpoint path and filter column");
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
      if (response.ok) {
        alert(`API created! Test it at http://localhost:8080${endpointPath}`);
        fetchApiConfigs();
        setEndpointPath("");
        setFilterCol("");
        setFilterVal("");
        setAggCol("");
      } else {
        alert("Failed to create API");
      }
    } catch (error) {
      console.error("Failed to create API");
    }
  };

  return (
    <div className="p-4 max-w-4xl mx-auto">
      <h2 className="text-2xl font-bold mb-4">File Manager</h2>
      <div className="grid grid-cols-2 gap-8">
        <div>
          <h3 className="text-lg font-semibold mb-2">Files</h3>
          <div className="grid gap-2">
            {files.map((file) => (
              <div
                key={file.id}
                className="p-2 border rounded-md flex justify-between items-center"
              >
                <span>{file.filename}</span>
                <div className="flex gap-2">
                  <Button
                    onClick={() => handleFileSelect(file.id)}
                    className="bg-blue-600 hover:bg-blue-700"
                  >
                    Select
                  </Button>
                  <Button
                    onClick={() => handleDeleteFile(file.id)}
                    className="bg-red-600 hover:bg-red-700"
                  >
                    Delete
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </div>
        {selectedFile && (
          <div>
            <h3 className="text-lg font-semibold mb-2">File Details</h3>
            <div className="mb-4">
              <label className="block text-sm font-medium">Sheet</label>
              <Select value={selectedSheet} onValueChange={setSelectedSheet}>
                <SelectTrigger>
                  <SelectValue placeholder="Select sheet" />
                </SelectTrigger>
                <SelectContent>
                  {selectedFile.sheets.map((sheet) => (
                    <SelectItem key={sheet} value={sheet}>
                      {sheet}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="mb-4">
              <label className="block text-sm font-medium">
                Columns (comma-separated)
              </label>
              <Input
                value={selectedColumns.join(", ")}
                onChange={(e) =>
                  setSelectedColumns(
                    e.target.value.split(",").map((c) => c.trim())
                  )
                }
              />
            </div>
            <Button onClick={handleUpdateFile} className="mb-4">
              Update File
            </Button>
            <h3 className="text-lg font-semibold mb-2">Create API</h3>
            <div className="mb-4">
              <label className="block text-sm font-medium">Endpoint Path</label>
              <Input
                value={endpointPath}
                onChange={(e) => setEndpointPath(e.target.value)}
                placeholder="/api/example"
              />
            </div>
            <div className="mb-4">
              <label className="block text-sm font-medium">Method</label>
              <Select value={method} onValueChange={setMethod}>
                <SelectTrigger>
                  <SelectValue placeholder="Select method" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="GET">GET</SelectItem>
                  <SelectItem value="POST">POST</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="grid grid-cols-3 gap-2 mb-4">
              <div>
                <label className="block text-sm font-medium">
                  Filter Column
                </label>
                <Input
                  value={filterCol}
                  onChange={(e) => setFilterCol(e.target.value)}
                />
              </div>
              <div>
                <label className="block text-sm font-medium">Operator</label>
                <Select value={filterOp} onValueChange={setFilterOp}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select operator" />
                  </SelectTrigger>
                  <SelectContent>
                    {[">", "<", "=", ">=", "<=", "!="].map((op) => (
                      <SelectItem key={op} value={op}>
                        {op}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <label className="block text-sm font-medium">Value</label>
                <Input
                  value={filterVal}
                  onChange={(e) => setFilterVal(e.target.value)}
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-2 mb-4">
              <div>
                <label className="block text-sm font-medium">
                  Aggregate Column
                </label>
                <Input
                  value={aggCol}
                  onChange={(e) => setAggCol(e.target.value)}
                />
              </div>
              <div>
                <label className="block text-sm font-medium">Function</label>
                <Select value={aggFunc} onValueChange={setAggFunc}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select function" />
                  </SelectTrigger>
                  <SelectContent>
                    {["sum", "avg", "count", "min", "max"].map((func) => (
                      <SelectItem key={func} value={func}>
                        {func}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            <Button onClick={handleCreateAPI}>Create API</Button>
            <h3 className="text-lg font-semibold mt-4 mb-2">Created APIs</h3>
            <div className="grid gap-2">
              {apiConfigs
                .filter((config) => config.file_id === selectedFile?.id)
                .map((config) => (
                  <div key={config.id} className="p-2 border rounded-md">
                    <p>
                      <strong>Path:</strong> http://localhost:8080
                      {config.endpoint_path}
                    </p>
                    <p>
                      <strong>Method:</strong> {config.method}
                    </p>
                    <p>
                      <strong>Query:</strong>{" "}
                      {JSON.stringify(config.query_logic)}
                    </p>
                  </div>
                ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default FileManagerPage;
