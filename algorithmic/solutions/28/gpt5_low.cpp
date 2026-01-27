#include <bits/stdc++.h>
using namespace std;

bool is_integer(const string &s) {
    if (s.empty()) return false;
    for (char c : s) if (!isdigit(c)) return false;
    return true;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int T;
    if (!(cin >> T)) return 0;
    for (int tc = 0; tc < T; ++tc) {
        int N;
        if (!(cin >> N)) break;
        set<string> seen;
        vector<string> words;
        string tok;
        while ((int)words.size() < N && (cin >> tok)) {
            if (is_integer(tok)) {
                int k = stoi(tok);
                for (int i = 0; i < k; ++i) {
                    string w;
                    if (!(cin >> w)) break;
                    if (seen.insert(w).second) words.push_back(w);
                    if ((int)words.size() >= N) break;
                }
            } else {
                if (seen.insert(tok).second) words.push_back(tok);
            }
        }
        cout << "answer";
        for (const auto &w : words) cout << ' ' << w;
        cout << "\n";
        cout.flush();
    }
    return 0;
}