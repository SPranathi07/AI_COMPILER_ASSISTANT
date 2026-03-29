#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include "lexer.h"


typedef struct {
    const char *word;
    TokenType   type;
} Keyword;

static Keyword keywords[] = {
    {"int",    TOKEN_INT},
    {"float",  TOKEN_FLOAT},
    {"void",   TOKEN_VOID},
    {"if",     TOKEN_IF},
    {"else",   TOKEN_ELSE},
    {"while",  TOKEN_WHILE},
    {"for",    TOKEN_FOR},
    {"return", TOKEN_RETURN},
    {"char",   TOKEN_CHAR},
    {NULL,     TOKEN_UNKNOWN}
};

const char *tokenTypeName(TokenType type) {
    switch (type) {
        case TOKEN_INT_LITERAL:   return "INT_LITERAL";
        case TOKEN_FLOAT_LITERAL: return "FLOAT_LITERAL";
        case TOKEN_IDENTIFIER:    return "IDENTIFIER";
        case TOKEN_INT:           return "KEYWORD(int)";
        case TOKEN_FLOAT:         return "KEYWORD(float)";
        case TOKEN_VOID:          return "KEYWORD(void)";
        case TOKEN_IF:            return "KEYWORD(if)";
        case TOKEN_ELSE:          return "KEYWORD(else)";
        case TOKEN_WHILE:         return "KEYWORD(while)";
        case TOKEN_FOR:           return "KEYWORD(for)";
        case TOKEN_RETURN:        return "KEYWORD(return)";
        case TOKEN_CHAR:          return "KEYWORD(char)";
        case TOKEN_PLUS:          return "PLUS";
        case TOKEN_MINUS:         return "MINUS";
        case TOKEN_MULTIPLY:      return "MULTIPLY";
        case TOKEN_DIVIDE:        return "DIVIDE";
        case TOKEN_MODULO:        return "MODULO";
        case TOKEN_EQ:            return "EQ";
        case TOKEN_NEQ:           return "NEQ";
        case TOKEN_LT:            return "LT";
        case TOKEN_GT:            return "GT";
        case TOKEN_LTE:           return "LTE";
        case TOKEN_GTE:           return "GTE";
        case TOKEN_AND:           return "AND";
        case TOKEN_OR:            return "OR";
        case TOKEN_NOT:           return "NOT";
        case TOKEN_ASSIGN:        return "ASSIGN";
        case TOKEN_LPAREN:        return "LPAREN";
        case TOKEN_RPAREN:        return "RPAREN";
        case TOKEN_LBRACE:        return "LBRACE";
        case TOKEN_RBRACE:        return "RBRACE";
        case TOKEN_LBRACKET:      return "LBRACKET";
        case TOKEN_RBRACKET:      return "RBRACKET";
        case TOKEN_SEMICOLON:     return "SEMICOLON";
        case TOKEN_COMMA:         return "COMMA";
        case TOKEN_EOF:           return "EOF";
        default:                  return "UNKNOWN";
    }
}

void advance(Lexer *lexer) {
    lexer->current = fgetc(lexer->file);
    lexer->column++;
    if (lexer->current == '\n') {
        lexer->line++;
        lexer->column = 0;
    }
}

char peek(Lexer *lexer) {
    char next = fgetc(lexer->file);
    ungetc(next, lexer->file);
    return next;
}

void skipWhitespace(Lexer *lexer) {
    while (lexer->current != EOF && isspace(lexer->current)) {
        advance(lexer);
    }
}

void skipLineComment(Lexer *lexer) {
    while (lexer->current != EOF && lexer->current != '\n') {
        advance(lexer);
    }
}

void skipBlockComment(Lexer *lexer) {
    advance(lexer);
    while (lexer->current != EOF) {
        if (lexer->current == '*' && peek(lexer) == '/') {
            advance(lexer);
            advance(lexer);
            return;
        }
        advance(lexer);
    }
    fprintf(stderr, "Error: Unterminated block comment\n");
}

TokenType checkKeyword(const char *word) {
    for (int i = 0; keywords[i].word != NULL; i++) {
        if (strcmp(keywords[i].word, word) == 0)
            return keywords[i].type;
    }
    return TOKEN_IDENTIFIER;
}

Token nextToken(Lexer *lexer) {
    Token token;
    token.value[0] = '\0';

    while (1) {
        skipWhitespace(lexer);
        if (lexer->current == '/' && peek(lexer) == '/') {
            advance(lexer);
            skipLineComment(lexer);
        } else if (lexer->current == '/' && peek(lexer) == '*') {
            advance(lexer);
            skipBlockComment(lexer);
        } else {
            break;
        }
    }

    token.line   = lexer->line;
    token.column = lexer->column;

    if (lexer->current == EOF) {
        token.type = TOKEN_EOF;
        strcpy(token.value, "EOF");
        return token;
    }

    if (isdigit(lexer->current)) {
        int i = 0, isFloat = 0;
        while (isdigit(lexer->current)) {
            token.value[i++] = lexer->current;
            advance(lexer);
        }
        if (lexer->current == '.' && isdigit(peek(lexer))) {
            isFloat = 1;
            token.value[i++] = lexer->current;
            advance(lexer);
            while (isdigit(lexer->current)) {
                token.value[i++] = lexer->current;
                advance(lexer);
            }
        }
        token.value[i] = '\0';
        token.type = isFloat ? TOKEN_FLOAT_LITERAL : TOKEN_INT_LITERAL;
        return token;
    }

    if (isalpha(lexer->current) || lexer->current == '_') {
        int i = 0;
        while (isalnum(lexer->current) || lexer->current == '_') {
            token.value[i++] = lexer->current;
            advance(lexer);
        }
        token.value[i] = '\0';
        token.type = checkKeyword(token.value);
        return token;
    }

    char c = lexer->current;
    token.value[0] = c;
    token.value[1] = '\0';
    advance(lexer);

    switch (c) {
        case '+': token.type = TOKEN_PLUS;      break;
        case '-': token.type = TOKEN_MINUS;     break;
        case '*': token.type = TOKEN_MULTIPLY;  break;
        case '%': token.type = TOKEN_MODULO;    break;
        case '(': token.type = TOKEN_LPAREN;    break;
        case ')': token.type = TOKEN_RPAREN;    break;
        case '{': token.type = TOKEN_LBRACE;    break;
        case '}': token.type = TOKEN_RBRACE;    break;
        case '[': token.type = TOKEN_LBRACKET;  break;
        case ']': token.type = TOKEN_RBRACKET;  break;
        case ';': token.type = TOKEN_SEMICOLON; break;
        case ',': token.type = TOKEN_COMMA;     break;
        case '/': token.type = TOKEN_DIVIDE;    break;
        case '=':
            if (lexer->current == '=') {
                token.value[1] = '='; token.value[2] = '\0';
                token.type = TOKEN_EQ;
                advance(lexer);
            } else token.type = TOKEN_ASSIGN;
            break;
        case '!':
            if (lexer->current == '=') {
                token.value[1] = '='; token.value[2] = '\0';
                token.type = TOKEN_NEQ;
                advance(lexer);
            } else token.type = TOKEN_NOT;
            break;
        case '<':
            if (lexer->current == '=') {
                token.value[1] = '='; token.value[2] = '\0';
                token.type = TOKEN_LTE;
                advance(lexer);
            } else token.type = TOKEN_LT;
            break;
        case '>':
            if (lexer->current == '=') {
                token.value[1] = '='; token.value[2] = '\0';
                token.type = TOKEN_GTE;
                advance(lexer);
            } else token.type = TOKEN_GT;
            break;
        case '&':
            if (lexer->current == '&') {
                token.value[1] = '&'; token.value[2] = '\0';
                token.type = TOKEN_AND;
                advance(lexer);
            } else token.type = TOKEN_UNKNOWN;
            break;
        case '|':
            if (lexer->current == '|') {
                token.value[1] = '|'; token.value[2] = '\0';
                token.type = TOKEN_OR;
                advance(lexer);
            } else token.type = TOKEN_UNKNOWN;
            break;
        default: token.type = TOKEN_UNKNOWN; break;
    }

    return token;
}

