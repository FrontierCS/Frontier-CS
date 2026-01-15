#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, R;
    if (!(cin >> N >> R)) return 0;

    for (int i = 0; i < N; i++) {
        int U, V;
        cin >> U >> V;
    }

    string t, tok;
    while (cin >> tok) {
        if ((int)tok.size() == N && all_of(tok.begin(), tok.end(), [](char c){ return c == '&' || c == '|'; })) {
            t = tok;
            break;
        }
    }

    if (t.empty()) t.assign(N, '&');

    cout << "! " << t << "\n";
    return 0;
}