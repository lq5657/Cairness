package service

import (
	"context"
	"errors"
	"testing"

	"example.com/go-http-user-service/internal/model"
	"example.com/go-http-user-service/internal/repo"
)

func TestUserServiceCreateSuccess(t *testing.T) {
	service := NewUserService(repo.NewUserRepo())

	user, err := service.Create(context.Background(), model.CreateUserRequest{
		Name:  "Ada Lovelace",
		Email: "ada@example.com",
	})
	if err != nil {
		t.Fatalf("Create returned error: %v", err)
	}
	if user.ID == "" {
		t.Fatal("Create returned user without ID")
	}
	if user.Email != "ada@example.com" {
		t.Fatalf("Create normalized email = %q", user.Email)
	}
}

func TestUserServiceCreateDuplicateEmail(t *testing.T) {
	service := NewUserService(repo.NewUserRepo())
	req := model.CreateUserRequest{Name: "Ada Lovelace", Email: "ada@example.com"}

	if _, err := service.Create(context.Background(), req); err != nil {
		t.Fatalf("first Create returned error: %v", err)
	}
	_, err := service.Create(context.Background(), req)
	if !errors.Is(err, ErrUserEmailExists) {
		t.Fatalf("second Create error = %v, want %v", err, ErrUserEmailExists)
	}
}

func TestUserServiceCreateRejectsInvalidInput(t *testing.T) {
	service := NewUserService(repo.NewUserRepo())

	_, err := service.Create(context.Background(), model.CreateUserRequest{
		Name:  "",
		Email: "not-an-email",
	})
	if !errors.Is(err, ErrInvalidUser) {
		t.Fatalf("Create error = %v, want %v", err, ErrInvalidUser)
	}
}
