package data

import (
	"encoding/json"
	"os"
	"path/filepath"
	"sort"
	"strconv"
	"strings"
)

const soberAppID = "org.vinegarhq.Sober"

type SteamAccount struct {
	SteamID, AccountName, PersonaName string
	MostRecent, Remembered, Club      bool
	Timestamp                         int64
}

type SoberProfile struct {
	Name                  string
	Club, Active, HasData bool
}

type Config struct {
	SteamClub        []string `json:"steam_club"`
	SoberClubProfile string   `json:"sober_club_profile"`
}

func env(name, fallback string) string {
	if v := os.Getenv(name); v != "" {
		return v
	}
	return fallback
}

func home() string { h, _ := os.UserHomeDir(); return h }

func configDir() string { return env("MFDCLUB_CONFIG_DIR", filepath.Join(home(), ".config", "mfdclub")) }
func dataDir() string {
	return env("MFDCLUB_DATA_DIR", filepath.Join(home(), ".local", "share", "mfdclub"))
}
func soberLive() string {
	return env("MFDCLUB_SOBER_DIR", filepath.Join(home(), ".var", "app", soberAppID))
}

func LoadConfig() Config {
	var c Config
	if b, err := os.ReadFile(filepath.Join(configDir(), "config.json")); err == nil {
		_ = json.Unmarshal(b, &c)
	}
	return c
}

func (c Config) isClubSteam(id, name string) bool {
	for _, k := range c.SteamClub {
		if strings.EqualFold(k, id) || strings.EqualFold(k, name) {
			return true
		}
	}
	return false
}

func steamRoots() []string {
	if d := os.Getenv("MFDCLUB_STEAM_DIR"); d != "" {
		return []string{d}
	}
	h := home()
	return []string{
		filepath.Join(h, ".local/share/Steam"),
		filepath.Join(h, ".steam/steam"),
		filepath.Join(h, ".var/app/com.valvesoftware.Steam/.local/share/Steam"),
	}
}

func SteamAccounts(c Config) []SteamAccount {
	for _, root := range steamRoots() {
		b, err := os.ReadFile(filepath.Join(root, "config", "loginusers.vdf"))
		if err != nil {
			continue
		}
		parsed, err := ParseVDF(string(b))
		if err != nil {
			return nil
		}
		users, _ := parsed["users"].(map[string]any)
		var out []SteamAccount
		for id, v := range users {
			u, _ := v.(map[string]any)
			s := func(k string) string { x, _ := u[k].(string); return x }
			ts, _ := strconv.ParseInt(s("Timestamp"), 10, 64)
			out = append(out, SteamAccount{
				SteamID: id, AccountName: s("AccountName"), PersonaName: s("PersonaName"),
				MostRecent: s("MostRecent") == "1" || s("mostrecent") == "1",
				Remembered: s("RememberPassword") == "1",
				Club:       c.isClubSteam(id, s("AccountName")), Timestamp: ts,
			})
		}
		sort.Slice(out, func(i, j int) bool { return out[i].Timestamp > out[j].Timestamp })
		return out
	}
	return nil
}

func nonEmptyDir(p string) bool {
	e, err := os.ReadDir(p)
	return err == nil && len(e) > 0
}

func SoberProfiles(c Config) []SoberProfile {
	active := ""
	if b, err := os.ReadFile(filepath.Join(dataDir(), "sober-state.json")); err == nil {
		var st struct {
			Active string `json:"active"`
		}
		_ = json.Unmarshal(b, &st)
		active = st.Active
	}
	names := map[string]bool{}
	pdir := filepath.Join(dataDir(), "sober-profiles")
	if entries, err := os.ReadDir(pdir); err == nil {
		for _, e := range entries {
			if e.IsDir() {
				names[e.Name()] = true
			}
		}
	}
	if active != "" {
		names[active] = true
	}
	var out []SoberProfile
	for n := range names {
		p := filepath.Join(pdir, n)
		if n == active {
			p = soberLive()
		}
		out = append(out, SoberProfile{Name: n, Club: n == c.SoberClubProfile, Active: n == active, HasData: nonEmptyDir(p)})
	}
	sort.Slice(out, func(i, j int) bool { return out[i].Name < out[j].Name })
	return out
}
