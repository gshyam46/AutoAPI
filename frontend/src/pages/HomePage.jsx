import { Link } from "react-router-dom";
import { Button } from "../components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "../components/ui/card";
import { ArrowRight, FileText, Upload, Zap } from "lucide-react";

function HomePage() {
  return (
    <div className="container mx-auto py-12 space-y-12">
      <div className="text-center space-y-4">
        <h1 className="text-4xl font-bold tracking-tight sm:text-5xl">
          Welcome to AutoAPI Ops
        </h1>
        <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
          Transform your data into powerful APIs with just a few clicks. Upload
          Excel/CSV files, design workflows, and visualize analytics
          effortlessly.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Upload className="h-5 w-5" />
              Upload Files
            </CardTitle>
            <CardDescription>
              Upload your Excel or CSV files to get started
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Link to="/upload">
              <Button className="w-full">
                Upload Now
                <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </Link>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileText className="h-5 w-5" />
              Manage Files
            </CardTitle>
            <CardDescription>
              View and manage your uploaded files
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Link to="/files">
              <Button className="w-full">
                View Files
                <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </Link>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Zap className="h-5 w-5" />
              Quick Start
            </CardTitle>
            <CardDescription>Get started with our platform</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            <Link to="/login">
              <Button variant="outline" className="w-full">
                Login
              </Button>
            </Link>
            <Link to="/register">
              <Button variant="secondary" className="w-full">
                Register
              </Button>
            </Link>
          </CardContent>
        </Card>
      </div>

      <div className="text-center space-y-4">
        <h2 className="text-2xl font-semibold">Why Choose AutoAPI Ops?</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-6">
          <div className="space-y-2">
            <h3 className="font-medium">Easy Integration</h3>
            <p className="text-muted-foreground">
              Seamlessly integrate with your existing systems
            </p>
          </div>
          <div className="space-y-2">
            <h3 className="font-medium">Powerful Analytics</h3>
            <p className="text-muted-foreground">
              Get insights from your data with built-in analytics
            </p>
          </div>
          <div className="space-y-2">
            <h3 className="font-medium">Secure & Reliable</h3>
            <p className="text-muted-foreground">
              Enterprise-grade security and reliability
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default HomePage;
