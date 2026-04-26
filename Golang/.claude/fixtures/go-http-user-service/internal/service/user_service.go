package service

import (
	"context"
	"errors"
	"fmt"
	"net/mail"
	"strings"
	"time"

	"example.com/go-http-user-service/internal/model"
	"example.com/go-http-user-service/internal/repo"
)

const createUserTimeout = 3 * time.Second

var (
	ErrInvalidUser     = errors.New("invalid user")
	ErrUserEmailExists = errors.New("user email already exists")
)

type UserRepository interface {
	FindByEmail(ctx context.Context, email string) (*model.User, error)
	Create(ctx context.Context, user *model.User) error
}

type UserService struct {
	repo UserRepository
	now  func() time.Time
}

func NewUserService(repo UserRepository) *UserService {
	return &UserService{
		repo: repo,
		now:  time.Now,
	}
}

func (s *UserService) Create(ctx context.Context, req model.CreateUserRequest) (*model.User, error) {
	name := strings.TrimSpace(req.Name)
	email := strings.ToLower(strings.TrimSpace(req.Email))
	if name == "" || !validEmail(email) {
		return nil, ErrInvalidUser
	}

	callCtx, cancel := context.WithTimeout(ctx, createUserTimeout)
	defer cancel()

	existing, err := s.repo.FindByEmail(callCtx, email)
	if err != nil && !errors.Is(err, repo.ErrNotFound) {
		return nil, fmt.Errorf("check user email: %w", err)
	}
	if existing != nil {
		return nil, ErrUserEmailExists
	}

	user := &model.User{
		Name:      name,
		Email:     email,
		CreatedAt: s.now().UTC(),
	}
	if err := s.repo.Create(callCtx, user); err != nil {
		if errors.Is(err, repo.ErrDuplicateEmail) {
			return nil, ErrUserEmailExists
		}
		return nil, fmt.Errorf("create user: %w", err)
	}
	return user, nil
}

func validEmail(value string) bool {
	_, err := mail.ParseAddress(value)
	return err == nil
}
