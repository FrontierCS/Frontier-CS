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

        set<string> all_words;
        int total_K_used = 0;

        for (char c = 'a'; c <= 'z'; ++c) {
            if ((int)all_words.size() >= N) break;

            string pref(1, c);
            int K = 1;

            while (true) {
                if ((int)all_words.size() >= N) break;

                int Kq = K;
                if (Kq > N) Kq = N;

                cout << "query " << pref << ' ' << Kq << '\n';
                cout.flush();

                int k;
                if (!(cin >> k)) return 0;
                vector<string> resp(k);
                for (int i = 0; i < k; ++i) {
                    cin >> resp[i];
                    all_words.insert(resp[i]);
                }
                total_K_used += Kq;

                if (k < Kq) {
                    // Overshoot: we received all words with this prefix
                    break;
                }
                if (Kq == N) {
                    // Requested maximum allowed, cannot increase further
                    break;
                }
                K <<= 1;
            }
        }

        // Prepare answer
        vector<string> res(all_words.begin(), all_words.end());

        cout << "answer";
        int printed = 0;
        for (int i = 0; i < N && i < (int)res.size(); ++i) {
            cout << ' ' << res[i];
            ++printed;
        }

        // If for some reason we have fewer than N words (should not happen with correct judge),
        // fill with dummy unique words not in the set, to satisfy format.
        while (printed < N) {
            string s = "a";
            while (all_words.count(s)) {
                int pos = (int)s.size() - 1;
                while (pos >= 0 && s[pos] == 'z') {
                    s[pos] = 'a';
                    --pos;
                }
                if (pos < 0) s.insert(s.begin(), 'a');
                else ++s[pos];
                if ((int)s.size() > 10) break;
            }
            cout << ' ' << s;
            all_words.insert(s);
            ++printed;
        }

        cout << '\n';
        cout.flush();
    }

    return 0;
}