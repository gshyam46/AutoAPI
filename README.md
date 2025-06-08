# AutoAPI

WIP

for api server running using flask api
cd backend\api_server
.venv\Scripts\activate
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload

for mock server running using go
cd backend\mock_server
go mod tidy
go run main.go

cd frontend
npm run dev
