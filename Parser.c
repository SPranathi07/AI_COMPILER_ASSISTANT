

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "lexer.h"

typedef enum {
    NODE_PROGRAM,
    NODE_FUNC_DECL,
    NODE_VAR_DECL,
    NODE_PARAM,
    NODE_BLOCK,
    NODE_IF,
    NODE_WHILE,
    NODE_FOR,
    NODE_RETURN,
    NODE_EXPR_STMT,
    NODE_ASSIGN,
    NODE_BINOP,
    NODE_UNOP,
    NODE_CALL,
    NODE_INDEX,
    NODE_IDENTIFIER,
    NODE_INT_LITERAL,
    NODE_FLOAT_LITERAL,
} NodeType;

typedef struct ASTNode ASTNode;

typedef struct {
    ASTNode **items;
    int       count;
    int       capacity;
} NodeList;

struct ASTNode {
    NodeType type;
    char     value[256];
    char     data_type[32];
    int      is_array;
    int      array_size;
    NodeList children;
};

static void nodeListInit(NodeList *l) {
    l->items = NULL; l->count = l->capacity = 0;
}

static void nodeListAppend(NodeList *l, ASTNode *n) {
    if (l->count >= l->capacity) {
        l->capacity = l->capacity ? l->capacity * 2 : 4;
        l->items = realloc(l->items, l->capacity * sizeof(ASTNode *));
    }
    l->items[l->count++] = n;
}

static ASTNode *newNode(NodeType type, const char *value) {
    ASTNode *n = calloc(1, sizeof(ASTNode));
    n->type = type;
    if (value) strncpy(n->value, value, 255);
    nodeListInit(&n->children);
    return n;
}

typedef struct {
    Lexer *lexer;
    Token  current;
    int    had_error;
} Parser;

static void parserError(Parser *p, const char *msg) {
    fprintf(stderr, "Parse error at %d:%d — %s (got '%s')\n",
            p->current.line, p->current.column,
            msg, p->current.value);

    fprintf(stdout, "{\"error\": true, \"line\": %d, \"column\": %d, "
            "\"message\": \"%s\", \"token\": \"%s\"}\n",
            p->current.line, p->current.column,
            msg, p->current.value);

    p->had_error = 1;
}

static void advance(Parser *p) {
    p->current = nextToken(p->lexer);
}

static int check(Parser *p, TokenType t) {
    return p->current.type == t;
}

static int match(Parser *p, TokenType t) {
    if (check(p, t)) { advance(p); return 1; }
    return 0;
}

static Token expect(Parser *p, TokenType t, const char *what) {
    Token tok = p->current;
    if (!check(p, t)) {
        char msg[256];
        snprintf(msg, sizeof(msg), "expected %s", what);
        parserError(p, msg);
    } else {
        advance(p);
    }
    return tok;
}

static int isTypeToken(Parser *p) {
    TokenType t = p->current.type;
    return t == TOKEN_INT || t == TOKEN_FLOAT ||
           t == TOKEN_CHAR || t == TOKEN_VOID;
}

static ASTNode *parseExpr(Parser *p);
static ASTNode *parseStmt(Parser *p);
static ASTNode *parseBlock(Parser *p);

static ASTNode *parsePrimary(Parser *p) {
    if (check(p, TOKEN_INT_LITERAL)) {
        ASTNode *n = newNode(NODE_INT_LITERAL, p->current.value);
        advance(p); return n;
    }
    if (check(p, TOKEN_FLOAT_LITERAL)) {
        ASTNode *n = newNode(NODE_FLOAT_LITERAL, p->current.value);
        advance(p); return n;
    }
    if (check(p, TOKEN_IDENTIFIER)) {
        char name[256];
        strncpy(name, p->current.value, 255);
        advance(p);
        if (check(p, TOKEN_LPAREN)) {
            advance(p);
            ASTNode *call = newNode(NODE_CALL, name);
            if (!check(p, TOKEN_RPAREN)) {
                nodeListAppend(&call->children, parseExpr(p));
                while (match(p, TOKEN_COMMA))
                    nodeListAppend(&call->children, parseExpr(p));
            }
            expect(p, TOKEN_RPAREN, "')'");
            return call;
        }
        return newNode(NODE_IDENTIFIER, name);
    }
    if (check(p, TOKEN_LPAREN)) {
        advance(p);
        ASTNode *inner = parseExpr(p);
        expect(p, TOKEN_RPAREN, "')'");
        return inner;
    }
    parserError(p, "expected expression");
    advance(p);
    return newNode(NODE_INT_LITERAL, "0");
}

static ASTNode *parsePostfix(Parser *p) {
    ASTNode *node = parsePrimary(p);
    while (check(p, TOKEN_LBRACKET)) {
        advance(p);
        ASTNode *idx = newNode(NODE_INDEX, "[]");
        nodeListAppend(&idx->children, node);
        nodeListAppend(&idx->children, parseExpr(p));
        expect(p, TOKEN_RBRACKET, "']'");
        node = idx;
    }
    return node;
}

static ASTNode *parseUnary(Parser *p) {
    if (check(p, TOKEN_NOT) || check(p, TOKEN_MINUS)) {
        char op[4]; strncpy(op, p->current.value, 3);
        advance(p);
        ASTNode *n = newNode(NODE_UNOP, op);
        nodeListAppend(&n->children, parseUnary(p));
        return n;
    }
    return parsePostfix(p);
}

#define PARSE_BINOP(funcName, nextLevel, ...)                          \
static ASTNode *funcName(Parser *p) {                                  \
    ASTNode *left = nextLevel(p);                                      \
    TokenType ops[] = { __VA_ARGS__, (TokenType)-1 };                  \
    while (1) {                                                        \
        int matched = 0;                                               \
        for (int i = 0; ops[i] != (TokenType)-1; i++) {               \
            if (check(p, ops[i])) { matched = 1; break; }             \
        }                                                              \
        if (!matched) break;                                           \
        char op[4]; strncpy(op, p->current.value, 3); advance(p);     \
        ASTNode *n = newNode(NODE_BINOP, op);                          \
        nodeListAppend(&n->children, left);                            \
        nodeListAppend(&n->children, nextLevel(p));                    \
        left = n;                                                      \
    }                                                                  \
    return left;                                                       \
}

PARSE_BINOP(parseMultiplicative, parseUnary,
            TOKEN_MULTIPLY, TOKEN_DIVIDE, TOKEN_MODULO)
PARSE_BINOP(parseAdditive, parseMultiplicative,
            TOKEN_PLUS, TOKEN_MINUS)
PARSE_BINOP(parseRelational, parseAdditive,
            TOKEN_LT, TOKEN_GT, TOKEN_LTE, TOKEN_GTE)
PARSE_BINOP(parseEquality, parseRelational,
            TOKEN_EQ, TOKEN_NEQ)
PARSE_BINOP(parseLogicalAnd, parseEquality,
            TOKEN_AND)
PARSE_BINOP(parseLogicalOr, parseLogicalAnd,
            TOKEN_OR)

static ASTNode *parseExpr(Parser *p) {
    ASTNode *left = parseLogicalOr(p);
    if (check(p, TOKEN_ASSIGN)) {
        if (left->type != NODE_IDENTIFIER && left->type != NODE_INDEX)
            parserError(p, "invalid assignment target");
        advance(p);
        ASTNode *n = newNode(NODE_ASSIGN, "=");
        nodeListAppend(&n->children, left);
        nodeListAppend(&n->children, parseExpr(p));
        return n;
    }
    return left;
}

static ASTNode *parseIfStmt(Parser *p) {
    ASTNode *node = newNode(NODE_IF, "if");
    expect(p, TOKEN_LPAREN, "'('");
    nodeListAppend(&node->children, parseExpr(p));
    expect(p, TOKEN_RPAREN, "')'");
    nodeListAppend(&node->children, parseStmt(p));
    if (match(p, TOKEN_ELSE))
        nodeListAppend(&node->children, parseStmt(p));
    return node;
}

static ASTNode *parseWhileStmt(Parser *p) {
    ASTNode *node = newNode(NODE_WHILE, "while");
    expect(p, TOKEN_LPAREN, "'('");
    nodeListAppend(&node->children, parseExpr(p));
    expect(p, TOKEN_RPAREN, "')'");
    nodeListAppend(&node->children, parseStmt(p));
    return node;
}

static ASTNode *parseVarDecl(Parser *p);

static ASTNode *parseForStmt(Parser *p) {
    ASTNode *node = newNode(NODE_FOR, "for");
    expect(p, TOKEN_LPAREN, "'('");
    if (isTypeToken(p)) {
        nodeListAppend(&node->children, parseVarDecl(p));
    } else {
        ASTNode *init = newNode(NODE_EXPR_STMT, "");
        if (!check(p, TOKEN_SEMICOLON))
            nodeListAppend(&init->children, parseExpr(p));
        expect(p, TOKEN_SEMICOLON, "';'");
        nodeListAppend(&node->children, init);
    }
    if (!check(p, TOKEN_SEMICOLON))
        nodeListAppend(&node->children, parseExpr(p));
    else
        nodeListAppend(&node->children, newNode(NODE_INT_LITERAL, "1"));
    expect(p, TOKEN_SEMICOLON, "';'");
    if (!check(p, TOKEN_RPAREN))
        nodeListAppend(&node->children, parseExpr(p));
    else
        nodeListAppend(&node->children, NULL);
    expect(p, TOKEN_RPAREN, "')'");
    nodeListAppend(&node->children, parseStmt(p));
    return node;
}

static ASTNode *parseReturnStmt(Parser *p) {
    ASTNode *node = newNode(NODE_RETURN, "return");
    if (!check(p, TOKEN_SEMICOLON))
        nodeListAppend(&node->children, parseExpr(p));
    expect(p, TOKEN_SEMICOLON, "';'");
    return node;
}

static ASTNode *parseBlock(Parser *p) {
    expect(p, TOKEN_LBRACE, "'{'");
    ASTNode *block = newNode(NODE_BLOCK, "");
    while (!check(p, TOKEN_RBRACE) && !check(p, TOKEN_EOF))
        nodeListAppend(&block->children, parseStmt(p));
    expect(p, TOKEN_RBRACE, "'}'");
    return block;
}

static ASTNode *parseStmt(Parser *p) {
    switch (p->current.type) {
        case TOKEN_IF:     advance(p); return parseIfStmt(p);
        case TOKEN_WHILE:  advance(p); return parseWhileStmt(p);
        case TOKEN_FOR:    advance(p); return parseForStmt(p);
        case TOKEN_RETURN: advance(p); return parseReturnStmt(p);
        case TOKEN_LBRACE:             return parseBlock(p);
        default:
            if (isTypeToken(p)) return parseVarDecl(p);
            {
                ASTNode *s = newNode(NODE_EXPR_STMT, "");
                if (!check(p, TOKEN_SEMICOLON))
                    nodeListAppend(&s->children, parseExpr(p));
                expect(p, TOKEN_SEMICOLON, "';'");
                return s;
            }
    }
}

static ASTNode *parseVarDecl(Parser *p) {
    ASTNode *node = newNode(NODE_VAR_DECL, "");
    strncpy(node->data_type, p->current.value, 31);
    advance(p);
    Token name = expect(p, TOKEN_IDENTIFIER, "variable name");
    strncpy(node->value, name.value, 255);
    if (match(p, TOKEN_LBRACKET)) {
        node->is_array = 1;
        if (check(p, TOKEN_INT_LITERAL)) {
            node->array_size = atoi(p->current.value);
            advance(p);
        }
        expect(p, TOKEN_RBRACKET, "']'");
    }
    if (match(p, TOKEN_ASSIGN))
        nodeListAppend(&node->children, parseExpr(p));
    expect(p, TOKEN_SEMICOLON, "';'");
    return node;
}

static ASTNode *parseParam(Parser *p) {
    ASTNode *param = newNode(NODE_PARAM, "");
    strncpy(param->data_type, p->current.value, 31);
    advance(p);
    Token name = expect(p, TOKEN_IDENTIFIER, "parameter name");
    strncpy(param->value, name.value, 255);
    if (match(p, TOKEN_LBRACKET)) {
        param->is_array = 1;
        expect(p, TOKEN_RBRACKET, "']'");
    }
    return param;
}

static ASTNode *parseDecl(Parser *p) {
    char saved_type[32];
    strncpy(saved_type, p->current.value, 31);
    advance(p);
    if (!check(p, TOKEN_IDENTIFIER)) {
        parserError(p, "expected identifier after type");
        advance(p);
        return NULL;
    }
    char saved_name[256];
    strncpy(saved_name, p->current.value, 255);
    advance(p);
    if (check(p, TOKEN_LPAREN)) {
        ASTNode *func = newNode(NODE_FUNC_DECL, saved_name);
        strncpy(func->data_type, saved_type, 31);
        advance(p);
        if (!check(p, TOKEN_RPAREN)) {
            if (check(p, TOKEN_VOID)) {
                advance(p);
            } else {
                nodeListAppend(&func->children, parseParam(p));
                while (match(p, TOKEN_COMMA))
                    nodeListAppend(&func->children, parseParam(p));
            }
        }
        expect(p, TOKEN_RPAREN, "')'");
        nodeListAppend(&func->children, parseBlock(p));
        return func;
    }
    ASTNode *var = newNode(NODE_VAR_DECL, saved_name);
    strncpy(var->data_type, saved_type, 31);
    if (match(p, TOKEN_LBRACKET)) {
        var->is_array = 1;
        if (check(p, TOKEN_INT_LITERAL)) {
            var->array_size = atoi(p->current.value);
            advance(p);
        }
        expect(p, TOKEN_RBRACKET, "']'");
    }
    if (match(p, TOKEN_ASSIGN))
        nodeListAppend(&var->children, parseExpr(p));
    expect(p, TOKEN_SEMICOLON, "';'");
    return var;
}

static ASTNode *parseProgram(Parser *p) {
    ASTNode *prog = newNode(NODE_PROGRAM, "program");
    while (!check(p, TOKEN_EOF)) {
        if (p->had_error) {
            p->had_error = 0;
            while (!check(p, TOKEN_EOF) &&
                   !check(p, TOKEN_SEMICOLON) &&
                   !check(p, TOKEN_RBRACE))
                advance(p);
            if (!check(p, TOKEN_EOF)) advance(p);
            continue;
        }
        ASTNode *d = parseDecl(p);
        if (d) nodeListAppend(&prog->children, d);
    }
    return prog;
}

static const char *nodeTypeName(NodeType t) {
    switch (t) {
        case NODE_PROGRAM:       return "Program";
        case NODE_FUNC_DECL:     return "FuncDecl";
        case NODE_VAR_DECL:      return "VarDecl";
        case NODE_PARAM:         return "Param";
        case NODE_BLOCK:         return "Block";
        case NODE_IF:            return "If";
        case NODE_WHILE:         return "While";
        case NODE_FOR:           return "For";
        case NODE_RETURN:        return "Return";
        case NODE_EXPR_STMT:     return "ExprStmt";
        case NODE_ASSIGN:        return "Assign";
        case NODE_BINOP:         return "BinOp";
        case NODE_UNOP:          return "UnOp";
        case NODE_CALL:          return "Call";
        case NODE_INDEX:         return "Index";
        case NODE_IDENTIFIER:    return "Identifier";
        case NODE_INT_LITERAL:   return "IntLit";
        case NODE_FLOAT_LITERAL: return "FloatLit";  
        default:                 return "?";
    }
}

static void printAST(ASTNode *node, int depth) {
    if (!node) { printf("%*s(null)\n", depth * 2, ""); return; }
    printf("%*s[%s]", depth * 2, "", nodeTypeName(node->type));
    if (node->value[0])     printf(" '%s'",  node->value);
    if (node->data_type[0]) printf(" : %s",  node->data_type);
    if (node->is_array)     printf("[%d]",   node->array_size);
    printf("\n");
    for (int i = 0; i < node->children.count; i++)
        printAST(node->children.items[i], depth + 1);
}

static void freeAST(ASTNode *node) {
    if (!node) return;
    for (int i = 0; i < node->children.count; i++)
        freeAST(node->children.items[i]);
    free(node->children.items);
    free(node);
}

ASTNode *parse(Lexer *lexer) {
    Parser p;
    p.lexer     = lexer;
    p.had_error = 0;
    p.current   = nextToken(lexer);
    return parseProgram(&p);
}

int main(int argc, char *argv[]) {
    if (argc < 2) {
        fprintf(stderr, "Usage: %s <source.c>\n", argv[0]);
        return 1;
    }

    FILE *file = fopen(argv[1], "r");
    if (!file) {
        fprintf(stderr, "Cannot open file: %s\n", argv[1]);
        fprintf(stdout,
            "{\"error\": true, \"line\": 0, \"column\": 0, "
            "\"message\": \"cannot open file\", \"token\": \"\"}\n");
        return 1;
    }
    FILE *file2 = fopen(argv[1], "r");
    Lexer lexer2;
    lexer2.file    = file2;
    lexer2.line    = 1;
    lexer2.column  = 0;
    lexer2.current = fgetc(file2);

    char token_seq[4096] = "";
    Token tok;
    int first = 1;
    do {
        tok = nextToken(&lexer2);
        if (tok.type != TOKEN_EOF && tok.type != TOKEN_UNKNOWN) {
            if (!first) strcat(token_seq, " ");
            strcat(token_seq, tokenTypeName(tok.type));
            first = 0;
        }
    } while (tok.type != TOKEN_EOF);
    fclose(file2);

    fprintf(stdout, "{\"tokens\": \"%s\"}\n", token_seq);
    Lexer lexer;
    lexer.file    = file;
    lexer.line    = 1;
    lexer.column  = 0;
    lexer.current = fgetc(lexer.file);

    ASTNode *ast = parse(&lexer);
    fprintf(stderr, "=== AST ===\n");
    printAST(ast, 0);

    if (!((Parser*)0)) {  
    }
    freeAST(ast);
    fclose(file);

    return 0;
}