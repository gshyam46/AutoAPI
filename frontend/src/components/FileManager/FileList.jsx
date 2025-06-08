import { Button } from "../ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../ui/card";
import { ScrollArea } from "../ui/scroll-area";

export function FileList({ files, onFileSelect, onFileDelete }) {
  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle className="text-xl">Files</CardTitle>
      </CardHeader>
      <CardContent>
        <ScrollArea className="h-[400px] pr-4">
          <div className="space-y-2">
            {files.map((file) => (
              <div
                key={file.id}
                className="flex items-center justify-between p-3 rounded-lg border bg-card hover:bg-accent transition-colors"
              >
                <span className="font-medium">{file.filename}</span>
                <div className="flex gap-2">
                  <Button
                    onClick={() => onFileSelect(file.id)}
                    variant="secondary"
                    size="sm"
                  >
                    Select
                  </Button>
                  <Button
                    onClick={() => onFileDelete(file.id)}
                    variant="destructive"
                    size="sm"
                  >
                    Delete
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}
