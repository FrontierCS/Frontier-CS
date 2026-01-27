#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    vector<vector<int>> queries;
    string line;

    // Read lines until we find a line starting with 1 (the guess), then output answers for stored queries.
    while (true) {
        if (!getline(cin, line)) break;
        if (!line.empty() && line.back() == '\r') line.pop_back();
        if (line.empty()) continue;

        istringstream iss(line);
        long long tll;
        if (!(iss >> tll)) continue;

        if (tll == 0) {
            vector<int> q;
            int x;
            while (iss >> x) q.push_back(x);
            queries.push_back(move(q));
        } else if (tll == 1) {
            vector<int> perm;
            int x;
            while (iss >> x) perm.push_back(x);
            for (auto &q : queries) {
                long long cnt = 0;
                int m = (int)min(q.size(), perm.size());
                for (int i = 0; i < m; ++i) if (q[i] == perm[i]) cnt++;
                cout << cnt << "\n";
            }
            return 0;
        } else {
            // Fallback: treat input as tokens, possibly "n p1 p2 ... pn"
            vector<long long> tokens;
            tokens.push_back(tll);
            long long y;
            while (iss >> y) tokens.push_back(y);
            while (cin >> y) tokens.push_back(y);

            if (!tokens.empty()) {
                long long n = tokens[0];
                if (n >= 1 && (long long)tokens.size() >= 1 + n) {
                    bool ok = true;
                    vector<int> perm;
                    perm.reserve((size_t)n);
                    for (long long i = 0; i < n; ++i) {
                        long long v = tokens[1 + i];
                        if (v < 1 || v > n) { ok = false; break; }
                        perm.push_back((int)v);
                    }
                    if (ok) {
                        vector<char> used((size_t)n + 1, 0);
                        for (int v : perm) { if (used[v]) { ok = false; break; } used[v] = 1; }
                    }
                    if (ok) {
                        cout << 1;
                        for (int v : perm) cout << " " << v;
                        cout << "\n";
                        return 0;
                    }
                }
            }
            return 0;
        }
    }

    return 0;
}