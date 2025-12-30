#include <bits/stdc++.h>
using namespace std;

const int MAXN = 320;
const int MAXM = 100000 + 5;

bool share_[MAXN][MAXN];
vector<int> col_rows[MAXM];

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    long long n0, m0;
    if (!(cin >> n0 >> m0)) return 0;

    bool swapped = false;
    if (n0 > m0) {
        swapped = true;
        swap(n0, m0);
    }

    int n = (int)n0;
    int m = (int)m0;

    vector<pair<int,int>> ans;

    if (n == 1) {
        // No rectangles possible, take all cells
        ans.reserve(m);
        for (int c = 0; c < m; ++c)
            ans.push_back({0, c});
    } else if (n == 2) {
        // Optimal construction: one column with both rows, others with a single row
        ans.reserve(m + 1);
        ans.push_back({0, 0});
        ans.push_back({1, 0});
        for (int c = 1; c < m; ++c)
            ans.push_back({0, c});
    } else {
        long long B = 1LL * n * (n - 1) / 2; // number of row pairs

        if (m >= B) {
            // Slender case: optimal construction using all pairs once + singletons
            ans.reserve((size_t)(m + B));
            int col = 0;
            for (int i = 0; i < n && col < m; ++i) {
                for (int j = i + 1; j < n && col < m; ++j) {
                    ans.push_back({i, col});
                    ans.push_back({j, col});
                    ++col;
                }
            }
            for (int c = col; c < m; ++c) {
                int r = c % n;
                ans.push_back({r, c});
            }
        } else {
            // Balanced case: random greedy without rectangles
            int total = n * m;
            vector<pair<int,int>> cells;
            cells.reserve(total);
            for (int r = 0; r < n; ++r)
                for (int c = 0; c < m; ++c)
                    cells.push_back({r, c});

            vector<int> ord(total);
            iota(ord.begin(), ord.end(), 0);

            mt19937_64 rng((unsigned)chrono::high_resolution_clock::now().time_since_epoch().count());

            int R;
            if (total <= 2000) R = 60;
            else if (total <= 10000) R = 40;
            else R = 25;

            vector<pair<int,int>> bestAns;
            size_t bestCount = 0;

            for (int iter = 0; iter < R; ++iter) {
                shuffle(ord.begin(), ord.end(), rng);

                for (int c = 0; c < m; ++c)
                    col_rows[c].clear();

                for (int i = 0; i < n; ++i)
                    memset(share_[i], 0, n * sizeof(bool));

                vector<pair<int,int>> cur;
                cur.reserve(total);

                for (int idx = 0; idx < total; ++idx) {
                    auto &p = cells[ord[idx]];
                    int r = p.first;
                    int c = p.second;
                    auto &vec = col_rows[c];

                    bool ok = true;
                    for (int rr : vec) {
                        if (share_[r][rr]) {
                            ok = false;
                            break;
                        }
                    }
                    if (!ok) continue;

                    for (int rr : vec) {
                        share_[r][rr] = true;
                        share_[rr][r] = true;
                    }
                    vec.push_back(r);
                    cur.push_back({r, c});
                }

                if (cur.size() > bestCount) {
                    bestCount = cur.size();
                    bestAns.swap(cur);
                }
            }

            ans.swap(bestAns);
        }
    }

    cout << ans.size() << "\n";
    for (auto &p : ans) {
        int r = p.first;
        int c = p.second;
        if (!swapped)
            cout << (r + 1) << " " << (c + 1) << "\n";
        else
            cout << (c + 1) << " " << (r + 1) << "\n";
    }

    return 0;
}