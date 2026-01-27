#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n;
    while ( (cin >> n) ) {
        vector<string> C(n, string(n, '0'));
        for (int i = 0; i < n; ++i) {
            string s;
            while ((int)s.size() < n) {
                string tok;
                if (!(cin >> tok)) break;
                for (char ch : tok) if (ch == '0' || ch == '1') s.push_back(ch);
            }
            if ((int)s.size() < n) s.resize(n, '0');
            C[i] = s.substr(0, n);
        }

        vector<int> p(n);
        iota(p.begin(), p.end(), 0);

        // Eliminate '10' patterns for i in [0..n-3] via triple rotations
        if (n >= 3) {
            int i = 0;
            while (i <= n - 3) {
                char c1 = C[p[i]][p[i+1]];
                char c2 = C[p[i+1]][p[i+2]];
                if (c1 == '1' && c2 == '0') {
                    int a = p[i], b = p[i+1], c = p[i+2];
                    p[i] = b; p[i+1] = c; p[i+2] = a;
                    i = max(0, i - 2);
                } else {
                    ++i;
                }
            }
        }

        // Compute c sequence around the cycle
        vector<int> c(n);
        for (int i = 0; i < n - 1; ++i) c[i] = C[p[i]][p[i+1]] - '0';
        c[n-1] = C[p[n-1]][p[0]] - '0';

        // Find boundaries in the cycle (indices i where c[i] != c[(i+1)%n])
        vector<int> boundaries;
        for (int i = 0; i < n; ++i) {
            int j = (i + 1) % n;
            if (c[i] != c[j]) boundaries.push_back(i);
        }

        // Determine candidate starting positions
        vector<int> candidates;
        if (boundaries.empty()) {
            candidates.resize(n);
            iota(candidates.begin(), candidates.end(), 0);
        } else {
            for (int idx : boundaries) {
                candidates.push_back((idx + 1) % n);
            }
            sort(candidates.begin(), candidates.end());
            candidates.erase(unique(candidates.begin(), candidates.end()), candidates.end());
        }

        // Choose lexicographically smallest rotation among candidates
        vector<int> best;
        bool first = true;
        for (int s : candidates) {
            vector<int> q(n);
            for (int k = 0; k < n; ++k) q[k] = p[(s + k) % n];
            if (first || q < best) {
                best = move(q);
                first = false;
            }
        }
        if (best.empty()) best = p;

        for (int i = 0; i < n; ++i) {
            if (i) cout << ' ';
            cout << (best[i] + 1);
        }
        cout << '\n';
    }
    return 0;
}