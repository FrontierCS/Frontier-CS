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

        unordered_set<string> found;
        found.reserve(N * 2);
        vector<string> words;
        words.reserve(N);

        auto add_words = [&](const vector<string>& v) {
            for (const auto& w : v) {
                if (found.insert(w).second) {
                    words.push_back(w);
                }
            }
        };

        auto do_query = [&](const string& S, int K) -> vector<string> {
            cout << "query " << S << " " << K << "\n";
            cout.flush();
            int k;
            if (!(cin >> k)) exit(0);
            vector<string> ret;
            ret.reserve(k);
            for (int i = 0; i < k; ++i) {
                string w;
                cin >> w;
                ret.push_back(w);
            }
            return ret;
        };

        for (char c = 'a'; c <= 'z' && (int)found.size() < N; ++c) {
            int K = 1;
            while ((int)found.size() < N) {
                if (K > N) K = N;
                vector<string> res = do_query(string(1, c), K);
                add_words(res);
                int k = (int)res.size();
                if (k < K) break;
                if (K == N) break;
                K <<= 1;
            }
        }

        if ((int)words.size() < N) {
            for (char c = 'a'; c <= 'z' && (int)words.size() < N; ++c) {
                vector<string> res = do_query(string(1, c), N);
                add_words(res);
            }
        }

        cout << "answer";
        for (int i = 0; i < N; ++i) {
            cout << " " << words[i];
        }
        cout << "\n";
        cout.flush();
    }
    return 0;
}