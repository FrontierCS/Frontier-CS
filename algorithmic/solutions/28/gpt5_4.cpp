#include <bits/stdc++.h>
using namespace std;

static bool isNumber(const string& s) {
    if (s.empty()) return false;
    size_t i = 0;
    if (s[0] == '+' || s[0] == '-') {
        if (s.size() == 1) return false;
        i = 1;
    }
    for (; i < s.size(); ++i) {
        if (!isdigit(static_cast<unsigned char>(s[i]))) return false;
    }
    return true;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int T;
    if (!(cin >> T)) return 0;

    for (int tc = 0; tc < T; ++tc) {
        int N;
        if (!(cin >> N)) return 0;

        unordered_set<string> us;
        us.reserve(N * 2 + 10);

        vector<string> words;
        words.reserve(N);

        while ((int)us.size() < N) {
            string tok;
            if (!(cin >> tok)) break;

            if (isNumber(tok)) {
                long long k = stoll(tok);
                for (long long i = 0; i < k; ++i) {
                    string w;
                    if (!(cin >> w)) break;
                    if (us.insert(w).second) words.push_back(w);
                }
            } else {
                if (us.insert(tok).second) words.push_back(tok);
                while ((int)us.size() < N) {
                    string w;
                    if (!(cin >> w)) break;
                    if (us.insert(w).second) words.push_back(w);
                }
                break;
            }
        }

        vector<string> ans(us.begin(), us.end());
        sort(ans.begin(), ans.end());
        if ((int)ans.size() > N) ans.resize(N);

        cout << "answer";
        for (const auto& w : ans) cout << " " << w;
        cout << "\n";
    }

    return 0;
}