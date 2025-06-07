import { Link } from "react-router-dom";
import { Button } from "../components/ui/button";

function HomePage() {
  return (
    <div className="p-4 max-w-4xl mx-auto">
      <h2 className="text-3xl font-bold mb-6 text-center">
        Welcome to AutoAPI Ops
      </h2>
      <p className="text-lg mb-8 text-gray-600 text-center">
        Automate your API operations with ease. Upload Excel/CSV files, design
        workflows, and visualize analytics.
      </p>
      <div className="flex justify-center gap-4">
        <Link to="/login">
          <Button className="bg-blue-600 hover:bg-blue-700">Login</Button>
        </Link>
        <Link to="/register">
          <Button className="bg-green-600 hover:bg-green-700">Register</Button>
        </Link>
        <Link to="/upload">
          <Button className="bg-purple-600 hover:bg-purple-700">
            Upload File
          </Button>
        </Link>
      </div>
    </div>
  );
}

export default HomePage;
