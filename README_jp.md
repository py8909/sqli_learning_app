# SQL Injection Learning App

Web開発者の初学者が **SQL Injection（SQLi）脆弱性の仕組みと対策**を実践的に学習するための教育用Webアプリケーションです。

本システムでは、本システムは，SQL インジェクションの攻撃原理と対策方法を，実際のWebアプリケーションの挙動を通して段階的に学習できることを目的としている．
---

# Overview

SQL Injectionは、現在でもWebアプリケーションにおける重大な脆弱性の一つとして知られています。   OWASP Top 10 においても、インジェクション攻撃は継続的に重要なセキュリティリスクとして報告されています。

Webアプリケーション開発者および開発初学者を対象として，SQLインジェクション攻撃の成立過程と対策原理を実践的に理解できる学習支援である.

本プロジェクトでは以下を目的として学習環境を開発しました。

- SQLインジェクション攻撃の仕組みを理解する
- 脆弱なコードを実際に攻撃して学習する
- 安全な実装方法を理解する
- Web開発者のセキュリティ教育に活用する

---

# Features

本アプリケーションでは以下の学習機能を提供します。

## イントロダクション

- SQLインジェクションとは？
- セキュリティの重要性
- このアプリで学べること
- 学習上の注意

##  演習問題

- ログインSQLi体験
- 検索フォームSQLi
- URLパラメータSQLi
- エラーベースSQLi
- ブラインドSQLi
- 脆弱コードの静的解析
- 動的解析デモ
- 安全なSQL（防御版）

## 確認問題

- イントロダクションの理解度テスト
- 演習の確認テスト

---

# System Architecture

Client (Browser)

↓

Frontend  
HTML / CSS 

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

## Development Tools

- Git
- GitHub
- VSCode

---

# Screenshots

### home

![home](docs/home.png)

### introduction SQLi

![introduction_SQLi](docs/intro_sqli.png)

### Exercise 1

![exercise1](docs/exercise1.png)

### introduction quiz

![introduction_quiz](docs/intro_quiz.png)

※画像は `docs/` フォルダに配置してください

