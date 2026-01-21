#include <bits/stdc++.h>
using namespace std;

static inline string trim(const string &s) {
    size_t b = 0;
    while (b < s.size() && isspace((unsigned char)s[b])) b++;
    size_t e = s.size();
    while (e > b && isspace((unsigned char)s[e - 1])) e--;
    return s.substr(b, e - b);
}

static inline vector<string> split_ws(const string &s) {
    vector<string> t;
    string cur;
    for (char c : s) {
        if (isspace((unsigned char)c)) {
            if (!cur.empty()) t.push_back(cur), cur.clear();
        } else cur.push_back(c);
    }
    if (!cur.empty()) t.push_back(cur);
    return t;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int m;
    if (!(cin >> m)) return 0;
    string line;
    getline(cin, line); // consume endline after m

    while (true) {
        if (!getline(cin, line)) break;
        line = trim(line);
        if (line.empty()) continue;

        if (line == "treasure") break;

        auto tok = split_ws(line);
        bool center = (!tok.empty() && tok[0] == "center");
        // Some judges might output "<k> left/right" or just "left/right".
        // We only need to know whether it's "center" or not.

        if (center) {
            cout << 0 << " left " << 0 << "\n";
        } else {
            int x = 1 % m;
            cout << x << " left " << x << "\n";
        }
        cout.flush();
    }

    return 0;
}