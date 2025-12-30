#include <bits/stdc++.h>
using namespace std;

static vector<string> do_query(const string& pref, int K) {
    cout << "query " << pref << " " << K << "\n" << flush;
    int k;
    if (!(cin >> k)) exit(0);
    vector<string> res;
    res.reserve(k);
    for (int i = 0; i < k; ++i) {
        string w;
        cin >> w;
        res.push_back(w);
    }
    return res;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int T;
    cin >> T;
    while (T--) {
        int N;
        cin >> N;

        set<string> dict;
        vector<char> nonempty;

        long long usedK = 0;

        // Determine which first letters exist (exactly) with K=1
        for (char c = 'a'; c <= 'z'; ++c) {
            usedK += 1;
            auto res = do_query(string(1, c), 1);
            for (auto &w : res) dict.insert(w);
            if (!res.empty()) nonempty.push_back(c);
        }

        if ((int)dict.size() < N) {
            int startK = min(64, N);
            for (char c : nonempty) {
                if ((int)dict.size() == N) break;
                if (N == 1) break;

                int K = startK;
                while (true) {
                    usedK += K;
                    auto res = do_query(string(1, c), K);
                    for (auto &w : res) dict.insert(w);

                    if ((int)res.size() < K || K == N) break;
                    K = min(N, K * 2);
                }
            }
        }

        cout << "answer";
        int cnt = 0;
        for (const auto& w : dict) {
            if (cnt >= N) break;
            cout << " " << w;
            ++cnt;
        }
        cout << "\n" << flush;
    }
    return 0;
}