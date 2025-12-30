#include <bits/stdc++.h>
using namespace std;

vector<pair<int,int>> run_rowpair(int n, int m, unsigned seed) {
    int R = min(n, m);
    int C = max(n, m);
    long long P = 1LL * R * (R - 1) / 2;
    double s = 1.0 + 8.0 * (double)P / (double)C;
    int D = (int)((1.0 + sqrt(s)) / 2.0);
    if (D < 2) D = 2;
    if (D > R) D = R;

    vector<char> pairUsed(R * R, 0);
    vector<vector<int>> colRows(C);
    vector<pair<int,int>> edges;
    edges.reserve(1LL * R * C);

    mt19937 rng(seed);
    vector<int> perm(R);
    iota(perm.begin(), perm.end(), 0);

    bool rowsAreOriginal = (n <= m);

    for (int c = 0; c < C; ++c) {
        auto &rowsList = colRows[c];
        shuffle(perm.begin(), perm.end(), rng);
        for (int idx = 0; idx < R && (int)rowsList.size() < D; ++idx) {
            int r = perm[idx];

            bool ok = true;
            for (int rr : rowsList) {
                int a = min(r, rr);
                int b = max(r, rr);
                if (pairUsed[a * R + b]) {
                    ok = false;
                    break;
                }
            }
            if (!ok) continue;

            for (int rr : rowsList) {
                int a = min(r, rr);
                int b = max(r, rr);
                pairUsed[a * R + b] = 1;
            }
            rowsList.push_back(r);

            if (rowsAreOriginal)
                edges.emplace_back(r + 1, c + 1);
            else
                edges.emplace_back(c + 1, r + 1);
        }
    }

    return edges;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    long long ln, lm;
    if (!(cin >> ln >> lm)) return 0;
    int n = (int)ln, m = (int)lm;

    vector<pair<int,int>> ans;

    if (n == 1 || m == 1) {
        ans.reserve(1LL * n * m);
        for (int i = 1; i <= n; ++i)
            for (int j = 1; j <= m; ++j)
                ans.emplace_back(i, j);
    } else if (n == 2 || m == 2) {
        if (n == 2) {
            ans.reserve(m + 1);
            ans.emplace_back(1, 1);
            ans.emplace_back(2, 1);
            for (int c = 2; c <= m; ++c)
                ans.emplace_back(1, c);
        } else { // m == 2
            ans.reserve(n + 1);
            ans.emplace_back(1, 1);
            ans.emplace_back(1, 2);
            for (int r = 2; r <= n; ++r)
                ans.emplace_back(r, 1);
        }
    } else {
        vector<pair<int,int>> best;
        for (unsigned seed = 1; seed <= 3; ++seed) {
            auto cand = run_rowpair(n, m, seed);
            if (cand.size() > best.size())
                best.swap(cand);
        }
        ans.swap(best);
    }

    cout << ans.size() << '\n';
    for (auto &p : ans)
        cout << p.first << ' ' << p.second << '\n';

    return 0;
}