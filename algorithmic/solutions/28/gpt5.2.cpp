#include <bits/stdc++.h>
using namespace std;

static vector<string> do_query(const string &pref, int K) {
    cout << "query " << pref << " " << K << "\n";
    cout.flush();

    int k;
    if (!(cin >> k)) exit(0);
    vector<string> res(k);
    for (int i = 0; i < k; i++) cin >> res[i];
    return res;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int T;
    if (!(cin >> T)) return 0;
    while (T--) {
        int N;
        cin >> N;

        unordered_set<string> got;
        got.reserve(N * 2 + 10);

        for (char c = 'a'; c <= 'z'; c++) {
            if ((int)got.size() >= N) break;

            string pref(1, c);
            int K = 1;

            while (true) {
                vector<string> ans = do_query(pref, K);
                for (auto &w : ans) got.insert(w);

                int k = (int)ans.size();
                if (k < K) break;
                if (K == N) break;

                int nextK = min(N, K * 2);
                if (nextK == K) break;
                K = nextK;
            }
        }

        cout << "answer";
        int printed = 0;
        for (const auto &w : got) {
            cout << " " << w;
            printed++;
            if (printed == N) break;
        }
        cout << "\n";
        cout.flush();
    }
    return 0;
}