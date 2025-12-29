#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int T;
    if (!(cin >> T)) return 0;
    while (T--) {
        int N;
        cin >> N;
        vector<string> all_words;
        long long usedK = 0;

        for (char c = 'a'; c <= 'z'; ++c) {
            if ((int)all_words.size() >= N) break;
            string prefix(1, c);
            int K = 1;

            while (true) {
                if ((int)all_words.size() >= N) break;

                if (K > N) K = N;

                cout << "query " << prefix << " " << K << '\n';
                cout.flush();

                usedK += K;

                int k;
                if (!(cin >> k)) return 0;
                vector<string> res(k);
                for (int i = 0; i < k; ++i) cin >> res[i];

                if (k == 0) {
                    // No words with this prefix
                    break;
                }

                if (k < K || K == N) {
                    // We got all words with this prefix
                    for (const string &w : res) {
                        all_words.push_back(w);
                    }
                    break;
                }

                // Need to increase K
                if (K * 2 > N) K = N;
                else K *= 2;
            }
        }

        // Output the final answer
        cout << "answer";
        for (const string &w : all_words) {
            cout << ' ' << w;
        }
        cout << '\n';
        cout.flush();
    }

    return 0;
}