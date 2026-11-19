// MFDClub GUI: read-only view of Steam accounts and Sober profiles.
package main

import (
	"fmt"
	"os/exec"

	"fyne.io/fyne/v2"
	"fyne.io/fyne/v2/app"
	"fyne.io/fyne/v2/container"
	"fyne.io/fyne/v2/dialog"
	"fyne.io/fyne/v2/widget"

	"github.com/mefoxdev/MFDClub/gui/internal/data"
)

func yn(b bool, s string) string {
	if b {
		return s
	}
	return ""
}

func table(headers []string, rows [][]string, empty string) fyne.CanvasObject {
	if len(rows) == 0 {
		return container.NewCenter(widget.NewLabel(empty))
	}
	t := widget.NewTable(
		func() (int, int) { return len(rows) + 1, len(headers) },
		func() fyne.CanvasObject { return widget.NewLabel("template text") },
		func(id widget.TableCellID, o fyne.CanvasObject) {
			l := o.(*widget.Label)
			if id.Row == 0 {
				l.SetText(headers[id.Col])
				l.TextStyle = fyne.TextStyle{Bold: true}
			} else {
				l.SetText(rows[id.Row-1][id.Col])
				l.TextStyle = fyne.TextStyle{}
			}
			l.Refresh()
		})
	widths := []float32{170, 170, 190, 160}
	for i := range headers {
		t.SetColumnWidth(i, widths[i%len(widths)])
	}
	return t
}

func build() (steam, sober fyne.CanvasObject, summary string) {
	cfg := data.LoadConfig()
	acc := data.SteamAccounts(cfg)
	var sr [][]string
	for _, a := range acc {
		sr = append(sr, []string{a.AccountName, a.PersonaName, a.SteamID,
			yn(a.Club, "club") + yn(a.MostRecent, " · last used") + yn(a.Remembered, " · remembered")})
	}
	prof := data.SoberProfiles(cfg)
	var pr [][]string
	for _, p := range prof {
		pr = append(pr, []string{p.Name, yn(p.Club, "club"), yn(p.Active, "active"), yn(p.HasData, "has session data")})
	}
	steam = table([]string{"Login", "Name", "SteamID64", "Status"}, sr, "No Steam accounts found")
	sober = table([]string{"Profile", "Club", "State", "Data"}, pr, "No Sober profiles (run `mfdclub sober init <name>`)")
	return steam, sober, fmt.Sprintf("Steam: %d · Sober profiles: %d", len(acc), len(prof))
}

// runCLI shells out to the mfdclub CLI so GUI and CLI share one implementation.
func runCLI(user string, args ...string) (string, error) {
	var full []string
	if user != "" {
		full = append(full, "--user", user)
	}
	full = append(full, args...)
	out, err := exec.Command("mfdclub", full...).CombinedOutput()
	return string(out), err
}

func main() {
	a := app.New()
	w := a.NewWindow("MFDClub")
	w.Resize(fyne.NewSize(760, 420))

	status := widget.NewLabel("")
	tabs := container.NewAppTabs()
	refresh := func() {
		sel := tabs.SelectedIndex()
		s, r, sum := build()
		tabs.Items = []*container.TabItem{
			container.NewTabItem("Steam", s),
			container.NewTabItem("Roblox (Sober)", r),
		}
		if sel > 0 {
			tabs.SelectIndex(sel)
		}
		tabs.Refresh()
		status.SetText(sum)
	}
	me := "(me)"
	users := append([]string{me}, data.LocalUsers()...)
	selected := ""
	picker := widget.NewSelect(users, func(sel string) {
		name := sel
		if sel == me {
			name = ""
		}
		selected = name
		if err := data.SetUser(name); err != nil {
			status.SetText("error: " + err.Error())
			return
		}
		refresh()
	})
	picker.SetSelected(me)
	refresh() // in case SetSelected did not fire the callback
	logout := widget.NewButton("Log out non-club…", func() {
		preview, err := runCLI(selected, "logout") // dry run
		if err != nil {
			dialog.ShowError(fmt.Errorf("%v\n%s", err, preview), w)
			return
		}
		dialog.ShowConfirm("Log out non-club accounts?", preview+"\nApply now?", func(ok bool) {
			if !ok {
				return
			}
			out, err := runCLI(selected, "logout", "--yes")
			if err != nil {
				dialog.ShowError(fmt.Errorf("%v\n%s", err, out), w)
			} else {
				dialog.ShowInformation("Done", out, w)
			}
			refresh()
		}, w)
	})
	left := container.NewHBox(widget.NewLabel("User:"), picker)
	right := container.NewHBox(logout, widget.NewButton("Refresh", refresh))
	top := container.NewBorder(nil, nil, left, right, status)
	w.SetContent(container.NewBorder(top, nil, nil, nil, tabs))
	w.ShowAndRun()
}
