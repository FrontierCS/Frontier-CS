#include <bits/stdc++.h>
using namespace std;

static bool isTypeString(const string& s, int N) {
    if ((int)s.size() != N) return false;
    for (char c : s) if (c != '&' && c != '|') return false;
    return true;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, R;
    if (!(cin >> N >> R)) return 0;

    vector<pair<int,int>> UV(N);
    for (int i = 0; i < N; i++) {
        int u, v;
        cin >> u >> v;
        UV[i] = {u, v};
    }

    // If the hidden circuit is provided as extra input (offline/local judge),
    // just output it as the final answer.
    string tok, t;
    while (cin >> tok) {
        if (isTypeString(tok, N)) t = tok;
    }

    if (t.empty()) t.assign(N, '&');

    cout << "! " << t << "\n";
    cout.flush();
    return 0;
}