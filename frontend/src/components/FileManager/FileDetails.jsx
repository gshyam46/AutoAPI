import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "../ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../ui/table";

export function FileDetails({
  selectedFile,
  selectedSheet,
  selectedColumns,
  onSheetChange,
  onColumnsChange,
  onUpdate,
}) {
  if (!selectedFile) return null;

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle className="text-xl">File Details</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <p className="text-sm font-medium">Filename</p>
            <p className="text-sm text-muted-foreground">
              {selectedFile.filename}
            </p>
          </div>
          <div>
            <p className="text-sm font-medium">Row Count</p>
            <p className="text-sm text-muted-foreground">
              {selectedFile.row_count}
            </p>
          </div>
        </div>

        {selectedFile.sheets.length > 1 && (
          <div className="space-y-2">
            <label className="text-sm font-medium">Select Sheet</label>
            <Select value={selectedSheet} onValueChange={onSheetChange}>
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
        )}

        <div className="space-y-2">
          <label className="text-sm font-medium">
            Select Columns (comma-separated)
          </label>
          <Input
            value={selectedColumns.join(", ")}
            onChange={(e) =>
              onColumnsChange(e.target.value.split(",").map((c) => c.trim()))
            }
          />
        </div>

        <Button onClick={onUpdate} className="w-full">
          Update File
        </Button>

        <div className="space-y-2">
          <h3 className="text-lg font-semibold">Preview (First 5 Rows)</h3>
          <div className="rounded-md border">
            <Table>
              <TableHeader>
                <TableRow>
                  {selectedFile.selected_columns.map((col) => (
                    <TableHead key={col}>{col}</TableHead>
                  ))}
                </TableRow>
              </TableHeader>
              <TableBody>
                {selectedFile.preview_data?.map((row, i) => (
                  <TableRow key={i}>
                    {selectedFile.selected_columns.map((col) => (
                      <TableCell key={col}>{row[col]}</TableCell>
                    ))}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
