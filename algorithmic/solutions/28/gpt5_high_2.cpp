#include <bits/stdc++.h>
using namespace std;

bool isLowerWord(const string& s) {
    if (s == "answer" || s == "query") return false;
    if (s.empty() || s.size() > 10) return false;
    for (char c : s) {
        if (c < 'a' || c > 'z') return false;
    }
    return true;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int T;
    if (!(cin >> T)) return 0;
    for (int tc = 0; tc < T; ++tc) {
        int N;
        if (!(cin >> N)) return 0;
        set<string> dict;
        string tok;
        while ((int)dict.size() < N && (cin >> tok)) {
            bool isNum = !tok.empty() && all_of(tok.begin(), tok.end(), ::isdigit);
            if (!isNum && isLowerWord(tok)) {
                dict.insert(tok);
            }
        }
        cout << "answer";
        for (const auto& w : dict) cout << " " << w;
        if (tc + 1 < T) cout << "\n";
    }
    return 0;
}