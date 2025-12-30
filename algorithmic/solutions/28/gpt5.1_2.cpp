#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int T;
    if (!(cin >> T)) return 0;
    while (T--) {
        int N;
        if (!(cin >> N)) return 0;

        vector<string> words;
        words.reserve(N);
        unordered_set<string> seen;
        seen.reserve(N * 2);
        seen.max_load_factor(0.7f);

        long long totalK = 0;

        for (char c = 'a'; c <= 'z'; ++c) {
            if ((int)words.size() >= N) break;

            string pref(1, c);
            int K = 1;

            while (true) {
                if ((int)words.size() >= N) break;

                cout << "query " << pref << " " << K << '\n';
                cout.flush();

                int k;
                if (!(cin >> k)) return 0;
                vector<string> res(k);
                for (int i = 0; i < k; ++i) cin >> res[i];

                totalK += K;

                for (auto &w : res) {
                    if (seen.insert(w).second) {
                        words.push_back(w);
                    }
                }

                if (k < K || K == N) break;
                K = min(K * 2, N);
            }
        }

        cout << "answer";
        for (const string &w : words) {
            cout << ' ' << w;
        }
        cout << '\n';
        cout.flush();
    }

    return 0;
}