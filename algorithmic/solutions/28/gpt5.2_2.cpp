#include <bits/stdc++.h>
using namespace std;

static inline bool readInt(int &x) {
    if (!(cin >> x)) return false;
    return true;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int T;
    if (!readInt(T)) return 0;

    while (T--) {
        int N;
        if (!readInt(N)) return 0;

        vector<string> all;
        all.reserve(N);
        unordered_set<string> seen;
        seen.reserve(N * 2);

        long long sumK = 0;

        auto doQuery = [&](const string &pref, int K) -> vector<string> {
            cout << "query " << pref << " " << K << "\n";
            cout.flush();
            sumK += K;

            int k;
            if (!(cin >> k)) exit(0);
            vector<string> words;
            words.reserve(k);
            for (int i = 0; i < k; i++) {
                string w;
                cin >> w;
                words.push_back(w);
            }
            return words;
        };

        for (char c = 'a'; c <= 'z' && (int)all.size() < N; c++) {
            string pref(1, c);
            int K = 1;

            while (true) {
                vector<string> got = doQuery(pref, K);
                int k = (int)got.size();

                if (k < K || K == N) {
                    for (auto &w : got) {
                        if (seen.insert(w).second) all.push_back(w);
                    }
                    break;
                }
                K = min(N, K * 2);
            }
        }

        // Safety: if still missing (should not happen), query remaining letters with K=N
        for (char c = 'a'; c <= 'z' && (int)all.size() < N; c++) {
            string pref(1, c);
            vector<string> got = doQuery(pref, N);
            for (auto &w : got) {
                if (seen.insert(w).second) all.push_back(w);
            }
        }

        cout << "answer";
        for (auto &w : all) cout << " " << w;
        cout << "\n";
        cout.flush();
    }

    return 0;
}