# SQL Injection Learning App

Web開発者および情報系学生が **SQL Injection（SQLi）脆弱性の仕組みと対策**を実践的に学習するための教育用Webアプリケーションです。

本システムでは、実際のWebアプリケーションを模した演習環境を提供し、SQLインジェクション攻撃を体験しながら脆弱性の理解と対策方法を学習できます。

---

# Overview

SQL Injectionは、現在でもWebアプリケーションにおける重大な脆弱性の一つとして知られています。   OWASP Top 10 においても、インジェクション攻撃は継続的に重要なセキュリティリスクとして報告されています。

しかしながら、開発者がSQLインジェクションを **実際に攻撃・検証しながら学習できる教育環境**は多くありません。

本プロジェクトでは以下を目的として学習環境を開発しました。

- SQLインジェクション攻撃の仕組みを理解する
- 脆弱なコードを実際に攻撃して学習する
- 安全な実装方法を理解する
- Web開発者のセキュリティ教育に活用する

---

# Features

本アプリケーションでは以下の学習機能を提供します。

## SQL Injection Exercises

- Login SQL Injection
- Search SQL Injection
- URL Parameter Injection
- Error-based SQL Injection
- Blind SQL Injection

## Learning Support

- Hint system
- Step-by-step exercises
- Vulnerability explanation
- Secure coding examples

## Management Features

- User authentication
- Learning progress management
- Admin dashboard (optional)

---

# System Architecture

Client (Browser)

↓

Frontend  
HTML / CSS / Bootstrap

↓

Backend  
Python Flask Application

↓

Database  
SQLite / PostgreSQL

---

# Technology Stack

## Backend

- Python
- Flask
- SQLAlchemy

## Database

- SQLite (development)
- PostgreSQL (production)

## Frontend

- HTML
- CSS
- Bootstrap

## Development Tools

- Git
- GitHub
- VSCode

---

# Screenshots

### Login Exercise

![login](docs/login.png)

### SQL Injection Exercise

![exercise](docs/exercise.png)

### Hint System

![hint](docs/hint.png)

※画像は `docs/` フォルダに配置してください

---

# Installation

## 1 Clone repository

```bash
git clone https://github.com/your-username/sqli-learning-app.git