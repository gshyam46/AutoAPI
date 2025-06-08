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
import { Label } from "../ui/label";

export function APIConfig({
  selectedFile,
  endpointPath,
  method,
  filterCol,
  filterOp,
  filterVal,
  aggCol,
  aggFunc,
  groupBy,
  onEndpointPathChange,
  onMethodChange,
  onFilterColChange,
  onFilterOpChange,
  onFilterValChange,
  onAggColChange,
  onAggFuncChange,
  onGroupByChange,
  onCreateAPI,
}) {
  if (!selectedFile) return null;

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle className="text-xl">Create API Endpoint</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label>Endpoint Path</Label>
            <Input
              value={endpointPath}
              onChange={(e) => onEndpointPathChange(e.target.value)}
              placeholder="/api/endpoint"
            />
          </div>
          <div className="space-y-2">
            <Label>Method</Label>
            <Select value={method} onValueChange={onMethodChange}>
              <SelectTrigger>
                <SelectValue placeholder="Select method" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="GET">GET</SelectItem>
                <SelectItem value="POST">POST</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>

        <div className="space-y-4">
          <h3 className="text-lg font-semibold">Filters</h3>
          <div className="grid grid-cols-3 gap-4">
            <div className="space-y-2">
              <Label>Column</Label>
              <Select value={filterCol} onValueChange={onFilterColChange}>
                <SelectTrigger>
                  <SelectValue placeholder="Select column" />
                </SelectTrigger>
                <SelectContent>
                  {selectedFile.selected_columns.map((col) => (
                    <SelectItem key={col} value={col}>
                      {col}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Operator</Label>
              <Select value={filterOp} onValueChange={onFilterOpChange}>
                <SelectTrigger>
                  <SelectValue placeholder="Select operator" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value=">">{">"}</SelectItem>
                  <SelectItem value="<">{"<"}</SelectItem>
                  <SelectItem value="=">{"="}</SelectItem>
                  <SelectItem value="!=">{"!="}</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Value</Label>
              <Input
                value={filterVal}
                onChange={(e) => onFilterValChange(e.target.value)}
                placeholder="Filter value"
              />
            </div>
          </div>
        </div>

        <div className="space-y-4">
          <h3 className="text-lg font-semibold">Aggregation</h3>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Column</Label>
              <Select value={aggCol} onValueChange={onAggColChange}>
                <SelectTrigger>
                  <SelectValue placeholder="Select column" />
                </SelectTrigger>
                <SelectContent>
                  {selectedFile.selected_columns.map((col) => (
                    <SelectItem key={col} value={col}>
                      {col}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Function</Label>
              <Select value={aggFunc} onValueChange={onAggFuncChange}>
                <SelectTrigger>
                  <SelectValue placeholder="Select function" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="avg">Average</SelectItem>
                  <SelectItem value="sum">Sum</SelectItem>
                  <SelectItem value="min">Minimum</SelectItem>
                  <SelectItem value="max">Maximum</SelectItem>
                  <SelectItem value="count">Count</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </div>

        <div className="space-y-2">
          <Label>Group By</Label>
          <Select value={groupBy} onValueChange={onGroupByChange}>
            <SelectTrigger>
              <SelectValue placeholder="Select column" />
            </SelectTrigger>
            <SelectContent>
              {selectedFile.selected_columns.map((col) => (
                <SelectItem key={col} value={col}>
                  {col}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <Button onClick={onCreateAPI} className="w-full">
          Create API
        </Button>
      </CardContent>
    </Card>
  );
}
