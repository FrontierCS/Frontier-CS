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

        vector<string> result;
        result.reserve(N);

        int collected = 0;

        for (char c = 'a'; c <= 'z' && collected < N; ++c) {
            int remaining = N - collected;
            string pref(1, c);

            int K = 1;
            vector<string> last;

            while (true) {
                K = min(K, remaining);
                cout << "query " << pref << " " << K << '\n' << flush;

                int k;
                if (!(cin >> k)) return 0;
                last.clear();
                last.reserve(k);
                for (int i = 0; i < k; ++i) {
                    string w;
                    cin >> w;
                    last.push_back(w);
                }

                if (k < K) {
                    result.insert(result.end(), last.begin(), last.end());
                    collected += k;
                    break;
                }

                // k == K
                if (K == remaining) {
                    result.insert(result.end(), last.begin(), last.end());
                    collected += k; // should reach N
                    break;
                }

                K = min(2 * K, remaining);
            }
        }

        cout << "answer";
        for (const auto &w : result) cout << ' ' << w;
        cout << '\n' << flush;
    }

    return 0;
}