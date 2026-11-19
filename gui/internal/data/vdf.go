// Package data reads the same files as the Python CLI (read-only).
package data

import (
	"errors"
	"strings"
)

// ParseVDF parses Valve KeyValues text into nested map[string]any (string or map).
func ParseVDF(text string) (map[string]any, error) {
	var toks []string // strings are prefixed with 's', braces are "{" / "}"
	for i := 0; i < len(text); {
		c := text[i]
		switch {
		case c == ' ' || c == '\t' || c == '\n' || c == '\r':
			i++
		case c == '/' && i+1 < len(text) && text[i+1] == '/':
			for i < len(text) && text[i] != '\n' {
				i++
			}
		case c == '{' || c == '}':
			toks = append(toks, string(c))
			i++
		case c == '"':
			i++
			var b strings.Builder
			for i < len(text) && text[i] != '"' {
				if text[i] == '\\' && i+1 < len(text) {
					switch text[i+1] {
					case 'n':
						b.WriteByte('\n')
					case 't':
						b.WriteByte('\t')
					case '\\', '"':
						b.WriteByte(text[i+1])
					default:
						b.WriteByte('\\')
						b.WriteByte(text[i+1])
					}
					i += 2
				} else {
					b.WriteByte(text[i])
					i++
				}
			}
			if i >= len(text) {
				return nil, errors.New("unterminated string")
			}
			i++
			toks = append(toks, "s"+b.String())
		default:
			return nil, errors.New("unexpected character")
		}
	}
	pos := 0
	var block func() (map[string]any, error)
	block = func() (map[string]any, error) {
		out := map[string]any{}
		for pos < len(toks) {
			t := toks[pos]
			if t == "}" {
				pos++
				return out, nil
			}
			if t == "{" {
				return nil, errors.New("expected key")
			}
			key := t[1:]
			pos++
			if pos >= len(toks) {
				return nil, errors.New("missing value")
			}
			if toks[pos] == "{" {
				pos++
				sub, err := block()
				if err != nil {
					return nil, err
				}
				out[key] = sub
			} else if toks[pos] == "}" {
				return nil, errors.New("missing value")
			} else {
				out[key] = toks[pos][1:]
				pos++
			}
		}
		return out, nil
	}
	return block()
}
