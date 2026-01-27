#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int T;
    if (!(cin >> T)) return 0;
    for (int tc = 0; tc < T; ++tc) {
        int N;
        cin >> N;

        unordered_set<string> seen;
        seen.reserve(N * 2);
        vector<string> all;

        for (char c = 'a'; c <= 'z'; ++c) {
            if ((int)all.size() >= N) break;

            string pref(1, c);
            int K = 1;

            while (true) {
                cout << "query " << pref << " " << K << "\n";
                cout.flush();

                int k;
                if (!(cin >> k)) return 0;
                vector<string> resp(k);
                for (int i = 0; i < k; ++i) cin >> resp[i];

                if (k < K || K == N) {
                    for (const string &w : resp) {
                        if (seen.insert(w).second) {
                            all.push_back(w);
                        }
                    }
                    break;
                } else {
                    // k == K and K < N, need to increase K
                    K = min(N, K * 2);
                }
            }
        }

        // If for some reason not all words collected (shouldn't happen), continue querying remaining letters
        for (char c = 'a'; c <= 'z' && (int)all.size() < N; ++c) {
            string pref(1, c);
            int K = 1;
            while (true) {
                cout << "query " << pref << " " << K << "\n";
                cout.flush();

                int k;
                if (!(cin >> k)) return 0;
                vector<string> resp(k);
                for (int i = 0; i < k; ++i) cin >> resp[i];

                if (k < K || K == N) {
                    for (const string &w : resp) {
                        if (seen.insert(w).second) {
                            all.push_back(w);
                        }
                    }
                    break;
                } else {
                    K = min(N, K * 2);
                }
            }
        }

        // Output the final answer
        cout << "answer";
        for (int i = 0; i < N && i < (int)all.size(); ++i) {
            cout << " " << all[i];
        }
        cout << "\n";
        cout.flush();
    }

    return 0;
}