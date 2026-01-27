#include <bits/stdc++.h>
using namespace std;

bool isSubseq(const vector<int>& p, const vector<int>& q) {
    int i = 0, j = 0;
    int n = (int)p.size(), m = (int)q.size();
    while (i < n && j < m) {
        if (p[i] == q[j]) ++j;
        ++i;
    }
    return j == m;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m, L, R, Sx, Sy, Lq;
    long long s_param;
    if (!(cin >> n >> m >> L >> R >> Sx >> Sy >> Lq >> s_param)) {
        return 0;
    }
    vector<int> q(Lq);
    for (int i = 0; i < Lq; ++i) cin >> q[i];

    // Basic check: all q[i] must be in [1, n]
    for (int x : q) {
        if (x < 1 || x > n) {
            cout << "NO\n";
            return 0;
        }
    }

    // Full-grid case: L=1, R=m
    if (L == 1 && R == m) {
        if (Sy != 1) {
            cout << "NO\n";
            return 0;
        }
        if (Sx != 1 && Sx != n) {
            cout << "NO\n";
            return 0;
        }
        vector<int> p;
        if (Sx == 1) {
            for (int r = 1; r <= n; ++r) p.push_back(r);
        } else {
            for (int r = n; r >= 1; --r) p.push_back(r);
        }
        if (!isSubseq(p, q)) {
            cout << "NO\n";
            return 0;
        }
        vector<pair<int,int>> path;
        if (Sx == 1) {
            // Start at (1,1), move row by row downwards
            for (int y = 1; y <= m; ++y) path.push_back({1, y});
            for (int r = 2; r <= n; ++r) {
                if (r % 2 == 0) {
                    path.push_back({r, m});
                    for (int y = m - 1; y >= 1; --y)
                        path.push_back({r, y});
                } else {
                    path.push_back({r, 1});
                    for (int y = 2; y <= m; ++y)
                        path.push_back({r, y});
                }
            }
        } else { // Sx == n
            // Start at (n,1), move row by row upwards
            for (int y = 1; y <= m; ++y) path.push_back({n, y});
            int cur_row = n;
            int dir = +1; // +1: left->right, -1: right->left
            for (int r = n - 1; r >= 1; --r) {
                if (dir == +1) {
                    path.push_back({r, m});
                    for (int y = m - 1; y >= 1; --y)
                        path.push_back({r, y});
                    dir = -1;
                } else {
                    path.push_back({r, 1});
                    for (int y = 2; y <= m; ++y)
                        path.push_back({r, y});
                    dir = +1;
                }
            }
        }
        cout << "YES\n";
        cout << path.size() << "\n";
        for (auto &pt : path) {
            cout << pt.first << " " << pt.second << "\n";
        }
        return 0;
    }

    // Central-band case: both corridors exist
    if (!(L > 1 && R < m)) {
        cout << "NO\n";
        return 0;
    }
    if (Sy != L) {
        cout << "NO\n";
        return 0;
    }

    auto buildRowOrder = [&](int dir) -> vector<int> {
        vector<int> p;
        p.push_back(Sx);
        if (dir == 1) {
            for (int r = Sx + 1; r <= n; ++r) p.push_back(r);
            for (int r = Sx - 1; r >= 1; --r) p.push_back(r);
        } else {
            for (int r = Sx - 1; r >= 1; --r) p.push_back(r);
            for (int r = Sx + 1; r <= n; ++r) p.push_back(r);
        }
        return p;
    };

    vector<int> p_plus = buildRowOrder(1);
    vector<int> p_minus = buildRowOrder(-1);
    bool ok_plus = isSubseq(p_plus, q);
    bool ok_minus = isSubseq(p_minus, q);

    if (!ok_plus && !ok_minus) {
        cout << "NO\n";
        return 0;
    }

    int chosen_dir = ok_plus ? 1 : -1;

    auto buildPathDirection = [&](int dir) -> vector<pair<int,int>> {
        vector<pair<int,int>> path;
        vector<char> visitedRow(n + 1, 0);

        // Start at (Sx, L) and traverse row Sx from L to R
        path.push_back({Sx, L});
        for (int y = L + 1; y <= R; ++y)
            path.push_back({Sx, y});
        visitedRow[Sx] = 1;
        int exitSide = 1; // 1 = R, 0 = L

        if (dir == 1) {
            // B1: rows Sx+1 .. n
            for (int row = Sx + 1; row <= n; ++row) {
                if (exitSide == 1) {
                    path.push_back({row, R});
                    for (int y = R - 1; y >= L; --y)
                        path.push_back({row, y});
                    exitSide = 0;
                } else {
                    path.push_back({row, L});
                    for (int y = L + 1; y <= R; ++y)
                        path.push_back({row, y});
                    exitSide = 1;
                }
                visitedRow[row] = 1;
            }
        } else {
            // dir == -1, B1: rows Sx-1 .. 1
            for (int row = Sx - 1; row >= 1; --row) {
                if (exitSide == 1) {
                    path.push_back({row, R});
                    for (int y = R - 1; y >= L; --y)
                        path.push_back({row, y});
                    exitSide = 0;
                } else {
                    path.push_back({row, L});
                    for (int y = L + 1; y <= R; ++y)
                        path.push_back({row, y});
                    exitSide = 1;
                }
                visitedRow[row] = 1;
            }
        }

        int row_end = (dir == 1 ? n : 1);
        int cur_col_corr;
        if (exitSide == 1) {
            path.push_back({row_end, R + 1});
            cur_col_corr = R + 1;
        } else {
            path.push_back({row_end, L - 1});
            cur_col_corr = L - 1;
        }

        if (dir == 1) {
            // Ascend from n down to 1
            for (int row = row_end; row >= 1; --row) {
                if (!visitedRow[row]) {
                    if (cur_col_corr == L - 1) {
                        // from left corridor into D at L, traverse to R, then to right corridor
                        path.push_back({row, L});
                        for (int y = L + 1; y <= R; ++y)
                            path.push_back({row, y});
                        path.push_back({row, R + 1});
                        cur_col_corr = R + 1;
                    } else {
                        // from right corridor into D at R, traverse to L, then to left corridor
                        path.push_back({row, R});
                        for (int y = R - 1; y >= L; --y)
                            path.push_back({row, y});
                        path.push_back({row, L - 1});
                        cur_col_corr = L - 1;
                    }
                    visitedRow[row] = 1;
                }
                if (row > 1) {
                    path.push_back({row - 1, cur_col_corr});
                }
            }
        } else {
            // dir == -1, ascend from 1 up to n
            for (int row = row_end; row <= n; ++row) {
                if (!visitedRow[row]) {
                    if (cur_col_corr == L - 1) {
                        path.push_back({row, L});
                        for (int y = L + 1; y <= R; ++y)
                            path.push_back({row, y});
                        path.push_back({row, R + 1});
                        cur_col_corr = R + 1;
                    } else {
                        path.push_back({row, R});
                        for (int y = R - 1; y >= L; --y)
                            path.push_back({row, y});
                        path.push_back({row, L - 1});
                        cur_col_corr = L - 1;
                    }
                    visitedRow[row] = 1;
                }
                if (row < n) {
                    path.push_back({row + 1, cur_col_corr});
                }
            }
        }

        return path;
    };

    vector<pair<int,int>> final_path = buildPathDirection(chosen_dir);

    cout << "YES\n";
    cout << final_path.size() << "\n";
    for (auto &pt : final_path) {
        cout << pt.first << " " << pt.second << "\n";
    }

    return 0;
}