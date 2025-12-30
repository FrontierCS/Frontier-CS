#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int T;
    if (!(cin >> T)) return 0;
    for (int tc = 0; tc < T; ++tc) {
        int N;
        if (!(cin >> N)) return 0;
        unordered_set<string> seen;
        seen.reserve(N * 2 + 10);
        vector<string> words;
        words.reserve(N);
        while ((int)words.size() < N) {
            int k;
            if (!(cin >> k)) return 0;
            for (int i = 0; i < k; ++i) {
                string s;
                cin >> s;
                if (seen.insert(s).second && (int)words.size() < N) {
                    words.push_back(s);
                }
            }
        }
        cout << "answer";
        for (const auto& w : words) {
            cout << " " << w;
        }
        cout << "\n";
        cout.flush();
    }
    return 0;
}