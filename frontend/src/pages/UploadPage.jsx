import { useState } from "react";
import { useForm, FormProvider, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";

import {
  Form,
  FormField,
  FormItem,
  FormLabel,
  FormControl,
  FormMessage,
} from "../components/ui/form";
import { Input } from "../components/ui/input";
import { Button } from "../components/ui/button";

// ✅ Schema (file is validated on submit instead)
const uploadSchema = z.object({
  file: z.any().refine((val) => val instanceof File && val.name !== "", {
    message: "Please upload a file",
  }),
});

function UploadPage() {
  const [message, setMessage] = useState("");

  const form = useForm({
    resolver: zodResolver(uploadSchema),
    defaultValues: {
      file: null,
    },
  });

  const onSubmit = async (values) => {
    const formData = new FormData();
    formData.append("file", values.file);

    try {
      const response = await fetch("http://localhost:8000/upload", {
        method: "POST",
        body: formData,
      });
      const data = await response.json();
      if (response.ok) {
        setMessage(
          `Uploaded ${data.filename}: ${
            data.rows
          } rows, Columns: ${data.columns.join(", ")}`
        );
        form.reset();
      } else {
        setMessage(data.detail || "Upload failed");
      }
    } catch (err) {
      setMessage("Failed to upload");
    }
  };

  return (
    <div className="p-4 max-w-md mx-auto">
      <h2 className="text-2xl font-bold mb-4">Upload File</h2>
      <FormProvider {...form}>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            <FormField
              control={form.control}
              name="file"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Choose CSV or Excel File</FormLabel>
                  <FormControl>
                    <Input
                      type="file"
                      accept=".csv,.xlsx"
                      onChange={(e) => {
                        field.onChange(e.target.files?.[0]);
                      }}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <Button type="submit">Upload</Button>
            {message && (
              <p
                className={`mt-2 ${
                  message.includes("Uploaded")
                    ? "text-green-500"
                    : "text-red-500"
                }`}
              >
                {message}
              </p>
            )}
          </form>
        </Form>
      </FormProvider>
    </div>
  );
}

export default UploadPage;
