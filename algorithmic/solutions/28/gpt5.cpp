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
        vector<string> words;
        words.reserve(N);

        for (char c = 'a'; c <= 'z'; ++c) {
            if ((int)words.size() >= N) break;
            string pref(1, c);
            int K = 1;
            while (true) {
                if ((int)words.size() >= N) break;
                cout << "query " << pref << " " << K << "\n" << flush;
                int k;
                if (!(cin >> k)) return 0;
                for (int i = 0; i < k; ++i) {
                    string s;
                    cin >> s;
                    if (seen.insert(s).second) {
                        words.push_back(s);
                    }
                }
                if (k < K || K == N) break;
                K = min(N, K * 2);
            }
        }

        // If somehow not all words collected, try to finish with broader prefixes
        // by cycling letters again (safety in case of unusual judge behavior).
        if ((int)words.size() < N) {
            for (char c = 'a'; c <= 'z' && (int)words.size() < N; ++c) {
                string pref(1, c);
                int K = N;
                cout << "query " << pref << " " << K << "\n" << flush;
                int k;
                if (!(cin >> k)) return 0;
                for (int i = 0; i < k; ++i) {
                    string s;
                    cin >> s;
                    if (seen.insert(s).second) {
                        words.push_back(s);
                    }
                }
            }
        }

        // Ensure we output exactly N words (trim if any excess due to defensive calls)
        if ((int)words.size() > N) words.resize(N);

        cout << "answer";
        for (int i = 0; i < N; ++i) {
            cout << " " << words[i];
        }
        cout << "\n" << flush;
    }
    return 0;
}