package main

import (
	"os"
	"path/filepath"
	"testing"

	"fyne.io/fyne/v2/test"
)

func TestBuildRenders(t *testing.T) {
	tmp := t.TempDir()
	t.Setenv("MFDCLUB_CONFIG_DIR", filepath.Join(tmp, "c"))
	t.Setenv("MFDCLUB_DATA_DIR", filepath.Join(tmp, "d"))
	t.Setenv("MFDCLUB_STEAM_DIR", filepath.Join(tmp, "s"))
	t.Setenv("MFDCLUB_SOBER_DIR", filepath.Join(tmp, "x"))
	os.MkdirAll(filepath.Join(tmp, "s", "config"), 0o755)
	os.WriteFile(filepath.Join(tmp, "s", "config", "loginusers.vdf"),
		[]byte(`"users" { "1" { "AccountName" "a" "PersonaName" "A" "Timestamp" "1" } }`), 0o644)

	a := test.NewApp()
	defer a.Quit()
	w := test.NewWindow(nil)
	steam, sober, sum := build()
	w.SetContent(steam)
	w.SetContent(sober)
	if sum != "Steam: 1 · Sober profiles: 0" {
		t.Fatalf("summary: %q", sum)
	}
}
