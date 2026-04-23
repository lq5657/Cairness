package repo

import (
	"context"
	"errors"
	"fmt"
	"sync"

	"example.com/go-http-user-service/internal/model"
)

var ErrNotFound = errors.New("user not found")

type UserRepo struct {
	mu      sync.Mutex
	byEmail map[string]*model.User
	nextID  int
}

func NewUserRepo() *UserRepo {
	return &UserRepo{
		byEmail: make(map[string]*model.User),
		nextID:  1,
	}
}

func (r *UserRepo) FindByEmail(ctx context.Context, email string) (*model.User, error) {
	if err := ctx.Err(); err != nil {
		return nil, fmt.Errorf("find user by email: %w", err)
	}

	r.mu.Lock()
	defer r.mu.Unlock()

	user, ok := r.byEmail[email]
	if !ok {
		return nil, ErrNotFound
	}
	copy := *user
	return &copy, nil
}

func (r *UserRepo) Create(ctx context.Context, user *model.User) error {
	if err := ctx.Err(); err != nil {
		return fmt.Errorf("create user: %w", err)
	}

	r.mu.Lock()
	defer r.mu.Unlock()

	if _, ok := r.byEmail[user.Email]; ok {
		return fmt.Errorf("create user: %w", ErrDuplicateEmail)
	}
	user.ID = fmt.Sprintf("u-%d", r.nextID)
	r.nextID++
	copy := *user
	r.byEmail[user.Email] = &copy
	return nil
}

var ErrDuplicateEmail = errors.New("user email already exists")
