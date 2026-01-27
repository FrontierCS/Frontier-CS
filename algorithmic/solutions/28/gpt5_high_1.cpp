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
        seen.reserve(N * 2);
        vector<string> result;
        result.reserve(N);
        
        while ((int)seen.size() < N) {
            int k;
            if (!(cin >> k)) k = 0;
            for (int i = 0; i < k; ++i) {
                string w;
                cin >> w;
                if (seen.insert(w).second) {
                    result.push_back(w);
                }
            }
        }
        
        cout << "answer";
        for (int i = 0; i < N; ++i) {
            cout << ' ' << result[i];
        }
        if (tc + 1 < T) cout << '\n';
    }
    return 0;
}