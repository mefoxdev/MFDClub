package data

import (
	"os"
	"path/filepath"
	"testing"
)

const sample = `"users"
{
	"1"
	{
		"AccountName"		"club_main"
		"PersonaName"		"Club"
		"RememberPassword"		"1"
		"MostRecent"		"0"
		"Timestamp"		"100"
	}
	"2"
	{
		"AccountName"		"personal"
		"PersonaName"		"Me"
		"MostRecent"		"1"
		"Timestamp"		"200"
	}
}
`

func TestSteamAndSober(t *testing.T) {
	tmp := t.TempDir()
	t.Setenv("MFDCLUB_STEAM_DIR", filepath.Join(tmp, "steam"))
	t.Setenv("MFDCLUB_DATA_DIR", filepath.Join(tmp, "data"))
	t.Setenv("MFDCLUB_SOBER_DIR", filepath.Join(tmp, "sober"))
	os.MkdirAll(filepath.Join(tmp, "steam", "config"), 0o755)
	os.WriteFile(filepath.Join(tmp, "steam", "config", "loginusers.vdf"), []byte(sample), 0o644)
	os.MkdirAll(filepath.Join(tmp, "sober"), 0o755)
	os.WriteFile(filepath.Join(tmp, "sober", "x"), []byte("1"), 0o644)
	os.MkdirAll(filepath.Join(tmp, "data", "sober-profiles", "me"), 0o755)
	os.WriteFile(filepath.Join(tmp, "data", "sober-state.json"), []byte(`{"active":"club"}`), 0o644)

	c := Config{SteamClub: []string{"CLUB_MAIN"}, SoberClubProfile: "club"}
	acc := SteamAccounts(c)
	if len(acc) != 2 || acc[0].AccountName != "personal" || acc[0].Club || !acc[1].Club || !acc[0].MostRecent {
		t.Fatalf("unexpected steam accounts: %+v", acc)
	}
	pr := SoberProfiles(c)
	if len(pr) != 2 || pr[0].Name != "club" || !pr[0].Active || !pr[0].Club || !pr[0].HasData || pr[1].HasData {
		t.Fatalf("unexpected sober profiles: %+v", pr)
	}
}

func TestBadVDF(t *testing.T) {
	if _, err := ParseVDF(`"a" "b`); err == nil {
		t.Fatal("expected error")
	}
}
