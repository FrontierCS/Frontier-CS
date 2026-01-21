#include <bits/stdc++.h>
using namespace std;

static inline string trim(const string &s) {
    size_t l = 0;
    while (l < s.size() && isspace((unsigned char)s[l])) l++;
    size_t r = s.size();
    while (r > l && isspace((unsigned char)s[r - 1])) r--;
    return s.substr(l, r - l);
}

enum class ObsType { TREASURE, CENTER, LEFT, RIGHT, UNKNOWN };

static ObsType readObservation() {
    string line;
    while (true) {
        if (!std::getline(cin, line)) return ObsType::UNKNOWN;
        line = trim(line);
        if (!line.empty()) break;
    }

    if (line == "treasure") return ObsType::TREASURE;
    if (line == "center") return ObsType::CENTER;
    if (line == "left") return ObsType::LEFT;
    if (line == "right") return ObsType::RIGHT;

    // More robust parsing: possibly "k left" / "k right"
    {
        stringstream ss(line);
        vector<string> tok;
        string t;
        while (ss >> t) tok.push_back(t);
        if (!tok.empty()) {
            if (tok[0] == "treasure") return ObsType::TREASURE;
            if (tok[0] == "center") return ObsType::CENTER;
            if (tok[0] == "left") return ObsType::LEFT;
            if (tok[0] == "right") return ObsType::RIGHT;
            if (isdigit((unsigned char)tok[0][0]) && tok.size() >= 2) {
                if (tok[1] == "left") return ObsType::LEFT;
                if (tok[1] == "right") return ObsType::RIGHT;
            }
        }
    }

    if (line.find("treasure") != string::npos) return ObsType::TREASURE;
    if (line.find("center") != string::npos) return ObsType::CENTER;
    if (line.find("left") != string::npos) return ObsType::LEFT;
    if (line.find("right") != string::npos) return ObsType::RIGHT;

    return ObsType::UNKNOWN;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int m;
    if (!(cin >> m)) return 0;
    string dummy;
    getline(cin, dummy); // consume endline after m

    ObsType obs = readObservation();
    int steps = 0;

    while (steps < 50000) {
        if (obs == ObsType::TREASURE || obs == ObsType::UNKNOWN) break;

        if (obs == ObsType::CENTER) {
            cout << 0 << " left " << 0 << endl; // initialize rotor
        } else {
            cout << 1 << " left " << 0 << endl; // take current marked edge, advance marker
        }

        steps++;
        obs = readObservation();
    }

    return 0;
}