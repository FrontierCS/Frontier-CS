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

        set<string> dict;

        for (char c = 'a'; c <= 'z' && (int)dict.size() < N; ++c) {
            cout << "query " << c << " " << N << endl;
            cout.flush();

            int k;
            if (!(cin >> k)) return 0;
            for (int i = 0; i < k; ++i) {
                string s;
                cin >> s;
                dict.insert(s);
            }
        }

        cout << "answer";
        for (const string &w : dict) {
            cout << ' ' << w;
        }
        cout << endl;
        cout.flush();
    }

    return 0;
}