package handler

import (
	"context"
	"encoding/json"
	"errors"
	"log/slog"
	"net/http"

	"example.com/go-http-user-service/internal/model"
	"example.com/go-http-user-service/internal/service"
)

type UserCreator interface {
	Create(ctx context.Context, req model.CreateUserRequest) (*model.User, error)
}

type UserHandler struct {
	service UserCreator
	logger  *slog.Logger
}

func NewUserHandler(service UserCreator, logger *slog.Logger) *UserHandler {
	return &UserHandler{service: service, logger: logger}
}

func (h *UserHandler) Create(w http.ResponseWriter, r *http.Request) {
	var req model.CreateUserRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeError(w, http.StatusBadRequest, "invalid_request")
		return
	}

	user, err := h.service.Create(r.Context(), req)
	if err != nil {
		switch {
		case errors.Is(err, service.ErrInvalidUser):
			writeError(w, http.StatusBadRequest, "invalid_user")
		case errors.Is(err, service.ErrUserEmailExists):
			writeError(w, http.StatusConflict, "email_exists")
		default:
			h.logger.Error("create user failed", slog.String("error", err.Error()))
			writeError(w, http.StatusInternalServerError, "internal_error")
		}
		return
	}

	writeJSON(w, http.StatusCreated, model.CreateUserResponse{
		ID:    user.ID,
		Name:  user.Name,
		Email: user.Email,
	})
}

func writeError(w http.ResponseWriter, status int, code string) {
	writeJSON(w, status, map[string]string{"code": code})
}

func writeJSON(w http.ResponseWriter, status int, value any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(value)
}
