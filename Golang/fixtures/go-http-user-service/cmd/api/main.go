package main

import (
	"log/slog"
	"net/http"
	"os"

	"example.com/go-http-user-service/internal/handler"
	"example.com/go-http-user-service/internal/repo"
	"example.com/go-http-user-service/internal/service"
)

func main() {
	logger := slog.New(slog.NewJSONHandler(os.Stdout, &slog.HandlerOptions{AddSource: true}))
	userRepo := repo.NewUserRepo()
	userService := service.NewUserService(userRepo)
	userHandler := handler.NewUserHandler(userService, logger)

	mux := http.NewServeMux()
	mux.HandleFunc("POST /api/v1/users", userHandler.Create)

	if err := http.ListenAndServe(":8080", mux); err != nil {
		logger.Error("api server stopped", slog.String("error", err.Error()))
	}
}
