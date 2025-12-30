#include <bits/stdc++.h>
using namespace std;

static inline bool is_number(const string &s) {
    if (s.empty()) return false;
    for (char c : s) if (!isdigit(static_cast<unsigned char>(c))) return false;
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
        unordered_set<string> seen;
        seen.reserve(N * 2 + 16);
        vector<string> words;
        words.reserve(N);

        while ((int)words.size() < N) {
            string tok;
            if (!(cin >> tok)) break;
            if (is_number(tok)) {
                int k = stoi(tok);
                for (int i = 0; i < k; ++i) {
                    string w; 
                    cin >> w;
                    if (seen.insert(w).second) {
                        words.push_back(w);
                        if ((int)words.size() == N) {
                            // consume remaining words in this k group if any
                            for (int j = i + 1; j + 1 <= k; ++j) {
                                string dummy; cin >> dummy;
                            }
                            break;
                        }
                    }
                }
            } else {
                // Direct mode: words follow directly
                if (seen.insert(tok).second) words.push_back(tok);
                while ((int)words.size() < N) {
                    string w;
                    cin >> w;
                    if (seen.insert(w).second) words.push_back(w);
                }
            }
        }

        sort(words.begin(), words.end());
        cout << "answer";
        for (auto &w : words) cout << " " << w;
        if (tc + 1 < T) cout << "\n";
    }
    return 0;
}