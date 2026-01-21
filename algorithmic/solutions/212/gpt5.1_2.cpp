#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m, L, R, Sx, Sy, Lq;
    long long s;
    if (!(cin >> n >> m >> L >> R >> Sx >> Sy >> Lq >> s)) return 0;
    vector<int> q(Lq);
    for (int i = 0; i < Lq; ++i) cin >> q[i];

    auto isSubsequence = [&](const vector<int>& p, const vector<int>& qseq) -> bool {
        int j = 0, Lq = (int)qseq.size();
        for (int x : p) {
            if (j < Lq && x == qseq[j]) ++j;
        }
        return j == Lq;
    };

    // Check q elements in [1..n]
    for (int x : q) {
        if (x < 1 || x > n) {
            cout << "NO\n";
            return 0;
        }
    }

    // n == 1 special case
    if (n == 1) {
        vector<int> p = {1};
        if (!isSubsequence(p, q)) {
            cout << "NO\n";
            return 0;
        }
        vector<pair<int,int>> path;
        int x = 1, y = L;
        path.emplace_back(x, y);
        for (int col = L + 1; col <= R; ++col) {
            y = col;
            path.emplace_back(x, y);
        }
        cout << "YES\n";
        cout << path.size() << "\n";
        for (auto &pr : path) cout << pr.first << " " << pr.second << "\n";
        return 0;
    }

    // Entire grid required: L == 1 && R == m
    if (L == 1 && R == m) {
        vector<pair<int,int>> path;
        // n == 2
        if (n == 2) {
            vector<int> p;
            if (Sx == 1) p = {1, 2};
            else p = {2, 1};
            if (!isSubsequence(p, q)) {
                cout << "NO\n";
                return 0;
            }
            if (Sx == 1) {
                int x = 1, y = 1;
                path.emplace_back(x, y);
                for (y = 2; y <= m; ++y) path.emplace_back(1, y);
                // row2
                path.emplace_back(2, m);
                for (y = m - 1; y >= 1; --y) path.emplace_back(2, y);
            } else { // Sx == 2
                int x = 2, y = 1;
                path.emplace_back(x, y);
                for (y = 2; y <= m; ++y) path.emplace_back(2, y);
                path.emplace_back(1, m);
                for (y = m - 1; y >= 1; --y) path.emplace_back(1, y);
            }
            cout << "YES\n";
            cout << path.size() << "\n";
            for (auto &pr : path) cout << pr.first << " " << pr.second << "\n";
            return 0;
        }

        // n >= 3
        if (Sx != 1 && Sx != n) {
            cout << "NO\n";
            return 0;
        }
        vector<int> p;
        if (Sx == 1) {
            for (int i = 1; i <= n; ++i) p.push_back(i);
        } else {
            for (int i = n; i >= 1; --i) p.push_back(i);
        }
        if (!isSubsequence(p, q)) {
            cout << "NO\n";
            return 0;
        }

        vector<pair<int,int>> path;
        if (Sx == 1) {
            int x = 1, y = 1;
            path.emplace_back(x, y);
            for (y = 2; y <= m; ++y) path.emplace_back(1, y);
            bool fromRight = true; // ended at column m
            for (int r = 2; r <= n; ++r) {
                if (fromRight) {
                    x = r; y = m;
                    path.emplace_back(x, y);
                    for (int col = m - 1; col >= 1; --col) {
                        y = col;
                        path.emplace_back(x, y);
                    }
                } else {
                    x = r; y = 1;
                    path.emplace_back(x, y);
                    for (int col = 2; col <= m; ++col) {
                        y = col;
                        path.emplace_back(x, y);
                    }
                }
                fromRight = !fromRight;
            }
        } else { // Sx == n
            int x = n, y = 1;
            path.emplace_back(x, y);
            for (y = 2; y <= m; ++y) path.emplace_back(n, y);
            bool fromRight = true;
            for (int r = n - 1; r >= 1; --r) {
                if (fromRight) {
                    x = r; y = m;
                    path.emplace_back(x, y);
                    for (int col = m - 1; col >= 1; --col) {
                        y = col;
                        path.emplace_back(x, y);
                    }
                } else {
                    x = r; y = 1;
                    path.emplace_back(x, y);
                    for (int col = 2; col <= m; ++col) {
                        y = col;
                        path.emplace_back(x, y);
                    }
                }
                fromRight = !fromRight;
            }
        }
        cout << "YES\n";
        cout << path.size() << "\n";
        for (auto &pr : path) cout << pr.first << " " << pr.second << "\n";
        return 0;
    }

    // Both sides corridor: L > 1 && R < m
    if (L > 1 && R < m) {
        vector<int> pDown, pUp;
        // Down-first order: Sx..n, Sx-1..1
        for (int i = Sx; i <= n; ++i) pDown.push_back(i);
        for (int i = Sx - 1; i >= 1; --i) pDown.push_back(i);

        bool useDown = false, useUp = false;
        if (isSubsequence(pDown, q)) {
            useDown = true;
        } else {
            // Up-first order: Sx, Sx-1..1, Sx+1..n
            pUp.push_back(Sx);
            for (int i = Sx - 1; i >= 1; --i) pUp.push_back(i);
            for (int i = Sx + 1; i <= n; ++i) pUp.push_back(i);
            if (isSubsequence(pUp, q)) {
                useUp = true;
            }
        }

        if (!useDown && !useUp) {
            cout << "NO\n";
            return 0;
        }

        vector<pair<int,int>> path;
        vector<vector<bool>> vis(n + 1, vector<bool>(m + 1, false));
        auto add = [&](int x, int y) {
            if (!vis[x][y]) {
                vis[x][y] = true;
                path.emplace_back(x, y);
            } else {
                // Should not happen in our construction; but ignore duplicates silently.
            }
        };

        if (useDown) {
            // Build Down-first path
            int x = Sx, y = L;
            add(x, y);
            for (int col = L + 1; col <= R; ++col) {
                y = col;
                add(x, y);
            }
            int side = R;
            for (int r = Sx + 1; r <= n; ++r) {
                x = r;
                add(x, side);
                if (side == L) {
                    for (int col = L + 1; col <= R; ++col) {
                        y = col;
                        add(x, y);
                    }
                    side = R;
                } else {
                    for (int col = R - 1; col >= L; --col) {
                        y = col;
                        add(x, y);
                    }
                    side = L;
                }
            }
            int corridorCol;
            if (side == L) {
                y = L - 1;
                add(x, y);
                corridorCol = y;
            } else {
                y = R + 1;
                add(x, y);
                corridorCol = y;
            }
            for (int r = n - 1; r >= 1; --r) {
                x = r;
                add(x, corridorCol);
                if (r < Sx) {
                    if (corridorCol == L - 1) {
                        y = L;
                        add(x, y);
                        for (int col = L + 1; col <= R; ++col) {
                            y = col;
                            add(x, y);
                        }
                        corridorCol = R + 1;
                        y = corridorCol;
                        add(x, y);
                    } else { // corridorCol == R + 1
                        y = R;
                        add(x, y);
                        for (int col = R - 1; col >= L; --col) {
                            y = col;
                            add(x, y);
                        }
                        corridorCol = L - 1;
                        y = corridorCol;
                        add(x, y);
                    }
                }
            }
        } else {
            // Build Up-first path
            int x = Sx, y = L;
            add(x, y);
            for (int col = L + 1; col <= R; ++col) {
                y = col;
                add(x, y);
            }
            int side = R;
            for (int r = Sx - 1; r >= 1; --r) {
                x = r;
                add(x, side);
                if (side == L) {
                    for (int col = L + 1; col <= R; ++col) {
                        y = col;
                        add(x, y);
                    }
                    side = R;
                } else {
                    for (int col = R - 1; col >= L; --col) {
                        y = col;
                        add(x, y);
                    }
                    side = L;
                }
            }
            int corridorCol;
            if (side == L) {
                y = L - 1;
                add(x, y);
                corridorCol = y;
            } else {
                y = R + 1;
                add(x, y);
                corridorCol = y;
            }
            for (int r = 2; r <= n; ++r) {
                x = r;
                add(x, corridorCol);
                if (r > Sx) {
                    if (corridorCol == L - 1) {
                        y = L;
                        add(x, y);
                        for (int col = L + 1; col <= R; ++col) {
                            y = col;
                            add(x, y);
                        }
                        corridorCol = R + 1;
                        y = corridorCol;
                        add(x, y);
                    } else { // corridorCol == R + 1
                        y = R;
                        add(x, y);
                        for (int col = R - 1; col >= L; --col) {
                            y = col;
                            add(x, y);
                        }
                        corridorCol = L - 1;
                        y = corridorCol;
                        add(x, y);
                    }
                }
            }
        }

        cout << "YES\n";
        cout << path.size() << "\n";
        for (auto &pr : path) cout << pr.first << " " << pr.second << "\n";
        return 0;
    }

    // Only one corridor side (L == 1 xor R == m but not both-full); not handled fully -> output NO
    cout << "NO\n";
    return 0;
}