package model

import "time"

type User struct {
	ID        string
	Name      string
	Email     string
	CreatedAt time.Time
}

type CreateUserRequest struct {
	Name  string `json:"name"`
	Email string `json:"email"`
}

type CreateUserResponse struct {
	ID    string `json:"id"`
	Name  string `json:"name"`
	Email string `json:"email"`
}
