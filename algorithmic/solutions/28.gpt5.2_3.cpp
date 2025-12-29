#include <bits/stdc++.h>
using namespace std;

static bool do_query(const string& pref, int K, vector<string>& out) {
    cout << "query " << pref << " " << K << "\n" << flush;
    int k;
    if (!(cin >> k)) return false;
    out.resize(k);
    for (int i = 0; i < k; i++) cin >> out[i];
    return true;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int T;
    if (!(cin >> T)) return 0;

    while (T--) {
        int N;
        cin >> N;

        set<string> words;
        long long sumK = 0;

        for (char c = 'a'; c <= 'z'; ++c) {
            string pref(1, c);
            int K = 1;
            while (true) {
                sumK += K;

                vector<string> got;
                if (!do_query(pref, K, got)) return 0;

                for (auto &w : got) words.insert(w);

                int k = (int)got.size();
                if (k < K || K == N) break;

                int nextK = K * 2;
                if (nextK > N) nextK = N;
                if (nextK == K) break;
                K = nextK;
            }
        }

        cout << "answer";
        int printed = 0;
        for (const auto& w : words) {
            if (printed == N) break;
            cout << " " << w;
            ++printed;
        }
        cout << "\n" << flush;
    }

    return 0;
}