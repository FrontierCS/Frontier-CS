#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int T;
    if (!(cin >> T)) return 0;

    while (T--) {
        int N;
        if (!(cin >> N)) return 0;
        vector<string> words(N);
        for (int i = 0; i < N; ++i) {
            if (!(cin >> words[i])) return 0;
        }
        cout << "answer";
        for (const auto &w : words) cout << ' ' << w;
        cout << '\n';
    }

    return 0;
}