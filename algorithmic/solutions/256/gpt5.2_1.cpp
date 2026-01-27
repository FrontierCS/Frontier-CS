#include <bits/stdc++.h>
using namespace std;

struct Query {
    int x1, y1, x2, y2;
};

struct Solver {
    int n;
    long long qcnt = 0;

    int ask(int x1, int y1, int x2, int y2) {
        cout << "? " << x1 << " " << y1 << " " << x2 << " " << y2 << "\n";
        cout.flush();
        int r;
        if (!(cin >> r)) exit(0);
        if (r == -1) exit(0);
        qcnt++;
        return r;
    }

    void bfsFill(vector<vector<int>> &val, int sx, int sy, int sval) {
        queue<pair<int,int>> qu;
        val[sx][sy] = sval;
        qu.push({sx, sy});
        static const int dxs[] = {2, -2, 0, 0, 1, -1};
        static const int dys[] = {0, 0, 2, -2, 1, -1};

        while (!qu.empty()) {
            auto [x, y] = qu.front();
            qu.pop();
            for (int k = 0; k < 6; k++) {
                int nx = x + dxs[k], ny = y + dys[k];
                if (nx < 1 || nx > n || ny < 1 || ny > n) continue;
                if (val[nx][ny] != -1) continue;
                if (((nx + ny) & 1) != ((x + y) & 1)) continue;

                int x1 = min(x, nx), y1 = min(y, ny);
                int x2 = max(x, nx), y2 = max(y, ny);
                int eq = ask(x1, y1, x2, y2); // 1 iff values equal (distance 2)
                val[nx][ny] = (eq ? val[x][y] : (val[x][y] ^ 1));
                qu.push({nx, ny});
            }
        }
    }

    static bool isPalindrome(const int *seq, int len) {
        for (int l = 0, r = len - 1; l < r; l++, r--) {
            if (seq[l] != seq[r]) return false;
        }
        return true;
    }

    static bool existPalUnique(const vector<vector<int>> &g, int x1, int y1, int x2, int y2) {
        int dx = x2 - x1, dy = y2 - y1;
        int len = dx + dy + 1;
        static int seq[110];
        int idx = 0;
        if (dx == 0) {
            for (int y = y1; y <= y2; y++) seq[idx++] = g[x1][y];
        } else {
            for (int x = x1; x <= x2; x++) seq[idx++] = g[x][y1];
        }
        return isPalindrome(seq, len);
    }

    static bool existPalBrutish(const vector<vector<int>> &g, int x1, int y1, int x2, int y2) {
        int dx = x2 - x1, dy = y2 - y1;
        int d = dx + dy;
        if (d < 2) return false;
        if (g[x1][y1] != g[x2][y2]) return false;

        if (dx == 0 || dy == 0) return existPalUnique(g, x1, y1, x2, y2);

        static int seq[110];

        auto simulateDownPos1 = [&](int p) -> bool {
            int x = x1, y = y1;
            seq[0] = g[x][y];
            for (int step = 0; step < d; step++) {
                if (step == p) x++;
                else y++;
                seq[step + 1] = g[x][y];
            }
            return isPalindrome(seq, d + 1);
        };

        auto simulateDownPos2 = [&](int p1, int p2) -> bool {
            int x = x1, y = y1;
            seq[0] = g[x][y];
            for (int step = 0; step < d; step++) {
                if (step == p1 || step == p2) x++;
                else y++;
                seq[step + 1] = g[x][y];
            }
            return isPalindrome(seq, d + 1);
        };

        auto simulateRightPos1 = [&](int p) -> bool {
            int x = x1, y = y1;
            seq[0] = g[x][y];
            for (int step = 0; step < d; step++) {
                if (step == p) y++;
                else x++;
                seq[step + 1] = g[x][y];
            }
            return isPalindrome(seq, d + 1);
        };

        auto simulateRightPos2 = [&](int p1, int p2) -> bool {
            int x = x1, y = y1;
            seq[0] = g[x][y];
            for (int step = 0; step < d; step++) {
                if (step == p1 || step == p2) y++;
                else x++;
                seq[step + 1] = g[x][y];
            }
            return isPalindrome(seq, d + 1);
        };

        if (dx == 1) {
            for (int p = 0; p < d; p++) if (simulateDownPos1(p)) return true;
            return false;
        }
        if (dy == 1) {
            for (int p = 0; p < d; p++) if (simulateRightPos1(p)) return true;
            return false;
        }
        if (dx == 2) {
            for (int p1 = 0; p1 < d; p1++) for (int p2 = p1 + 1; p2 < d; p2++)
                if (simulateDownPos2(p1, p2)) return true;
            return false;
        }
        if (dy == 2) {
            for (int p1 = 0; p1 < d; p1++) for (int p2 = p1 + 1; p2 < d; p2++)
                if (simulateRightPos2(p1, p2)) return true;
            return false;
        }

        if (d <= 11) {
            vector<int> mv(d, 0);
            for (int i = 0; i < dx; i++) mv[d - 1 - i] = 1; // 0..0 1..1
            do {
                int x = x1, y = y1;
                seq[0] = g[x][y];
                for (int step = 0; step < d; step++) {
                    if (mv[step] == 1) x++;
                    else y++;
                    seq[step + 1] = g[x][y];
                }
                if (isPalindrome(seq, d + 1)) return true;
            } while (next_permutation(mv.begin(), mv.end()));
            return false;
        }

        return false;
    }

    static bool existPalDP(const vector<vector<int>> &g, int x1, int y1, int x2, int y2) {
        int dx = x2 - x1, dy = y2 - y1;
        int d = dx + dy;
        if (d < 2) return false;
        if (g[x1][y1] != g[x2][y2]) return false;

        int tmax = d / 2;
        vector<vector<unsigned char>> cur(dx + 1, vector<unsigned char>(dx + 1, 0));
        vector<vector<unsigned char>> nxt(dx + 1, vector<unsigned char>(dx + 1, 0));
        cur[0][dx] = 1;

        for (int t = 0; t < tmax; t++) {
            for (int i = 0; i <= dx; i++) fill(nxt[i].begin(), nxt[i].end(), 0);

            for (int i = 0; i <= dx; i++) {
                int j = t - i;
                if (j < 0 || j > dy) continue;
                for (int i2 = 0; i2 <= dx; i2++) {
                    if (!cur[i][i2]) continue;
                    int j2 = (d - t) - i2;
                    if (j2 < 0 || j2 > dy) continue;

                    for (int sd = 0; sd < 2; sd++) { // 0: down, 1: right
                        int ni = i + (sd == 0 ? 1 : 0);
                        int nj = (t + 1) - ni;
                        if (ni < 0 || ni > dx || nj < 0 || nj > dy) continue;

                        for (int eu = 0; eu < 2; eu++) { // 0: left, 1: up (backward move)
                            int ni2 = i2 - (eu == 1 ? 1 : 0);
                            int nj2 = (d - (t + 1)) - ni2;
                            if (ni2 < 0 || ni2 > dx || nj2 < 0 || nj2 > dy) continue;

                            if (g[x1 + ni][y1 + nj] == g[x1 + ni2][y1 + nj2]) {
                                nxt[ni][ni2] = 1;
                            }
                        }
                    }
                }
            }
            cur.swap(nxt);
        }

        if ((d & 1) == 0) {
            for (int i = 0; i <= dx; i++) {
                int j = tmax - i;
                if (j < 0 || j > dy) continue;
                if (cur[i][i]) return true;
            }
            return false;
        } else {
            for (int i = 0; i <= dx; i++) {
                int j = tmax - i;
                if (j < 0 || j > dy) continue;
                for (int i2 = 0; i2 <= dx; i2++) {
                    if (!cur[i][i2]) continue;
                    int j2 = (d - tmax) - i2; // = tmax+1 - i2
                    if (j2 < 0 || j2 > dy) continue;
                    int dist = abs(i - i2) + abs(j - j2);
                    if (dist == 1) return true;
                }
            }
            return false;
        }
    }

    static bool existPal(const vector<vector<int>> &g, int x1, int y1, int x2, int y2) {
        int dx = x2 - x1, dy = y2 - y1;
        int d = dx + dy;
        if (d < 2) return false;
        if (g[x1][y1] != g[x2][y2]) return false;

        if (dx == 0 || dy == 0) return existPalUnique(g, x1, y1, x2, y2);
        if (dx <= 2 || dy <= 2 || d <= 11) return existPalBrutish(g, x1, y1, x2, y2);
        return existPalDP(g, x1, y1, x2, y2);
    }

    Query findDifference(const vector<vector<int>> &g0, const vector<vector<int>> &g1) {
        // First: small perimeters
        for (int D = 3; D <= 11; D++) {
            for (int dx = 0; dx <= D; dx++) {
                int dy = D - dx;
                for (int x1 = 1; x1 + dx <= n; x1++) {
                    for (int y1 = 1; y1 + dy <= n; y1++) {
                        int x2 = x1 + dx, y2 = y1 + dy;
                        bool p0 = existPal(g0, x1, y1, x2, y2);
                        bool p1 = existPal(g1, x1, y1, x2, y2);
                        if (p0 != p1) return {x1, y1, x2, y2};
                    }
                }
            }
        }

        // Lines from (1,1)
        for (int y2 = 3; y2 <= n; y2++) {
            bool p0 = existPal(g0, 1, 1, 1, y2);
            bool p1 = existPal(g1, 1, 1, 1, y2);
            if (p0 != p1) return {1, 1, 1, y2};
        }
        for (int x2 = 3; x2 <= n; x2++) {
            bool p0 = existPal(g0, 1, 1, x2, 1);
            bool p1 = existPal(g1, 1, 1, x2, 1);
            if (p0 != p1) return {1, 1, x2, 1};
        }

        // Thin rectangles: dx=1,2 and dy=1,2
        for (int dy = 1; dy <= n - 1; dy++) {
            for (int x1 = 1; x1 + 1 <= n; x1++) {
                for (int y1 = 1; y1 + dy <= n; y1++) {
                    int x2 = x1 + 1, y2 = y1 + dy;
                    if ((x2 - x1) + (y2 - y1) < 2) continue;
                    bool p0 = existPal(g0, x1, y1, x2, y2);
                    bool p1 = existPal(g1, x1, y1, x2, y2);
                    if (p0 != p1) return {x1, y1, x2, y2};
                }
            }
        }
        for (int dx = 1; dx <= n - 1; dx++) {
            for (int x1 = 1; x1 + dx <= n; x1++) {
                for (int y1 = 1; y1 + 1 <= n; y1++) {
                    int x2 = x1 + dx, y2 = y1 + 1;
                    if ((x2 - x1) + (y2 - y1) < 2) continue;
                    bool p0 = existPal(g0, x1, y1, x2, y2);
                    bool p1 = existPal(g1, x1, y1, x2, y2);
                    if (p0 != p1) return {x1, y1, x2, y2};
                }
            }
        }

        for (int dy = 0; dy <= n - 1; dy++) {
            for (int x1 = 1; x1 + 2 <= n; x1++) {
                for (int y1 = 1; y1 + dy <= n; y1++) {
                    int x2 = x1 + 2, y2 = y1 + dy;
                    if ((x2 - x1) + (y2 - y1) < 2) continue;
                    bool p0 = existPal(g0, x1, y1, x2, y2);
                    bool p1 = existPal(g1, x1, y1, x2, y2);
                    if (p0 != p1) return {x1, y1, x2, y2};
                }
            }
        }
        for (int dx = 0; dx <= n - 1; dx++) {
            for (int x1 = 1; x1 + dx <= n; x1++) {
                for (int y1 = 1; y1 + 2 <= n; y1++) {
                    int x2 = x1 + dx, y2 = y1 + 2;
                    if ((x2 - x1) + (y2 - y1) < 2) continue;
                    bool p0 = existPal(g0, x1, y1, x2, y2);
                    bool p1 = existPal(g1, x1, y1, x2, y2);
                    if (p0 != p1) return {x1, y1, x2, y2};
                }
            }
        }

        // Heavy fallback: DP from (1,1) to every reachable cell
        for (int x2 = 1; x2 <= n; x2++) {
            for (int y2 = 1; y2 <= n; y2++) {
                int d = (x2 - 1) + (y2 - 1);
                if (d < 2) continue;
                bool p0 = existPalDP(g0, 1, 1, x2, y2);
                bool p1 = existPalDP(g1, 1, 1, x2, y2);
                if (p0 != p1) return {1, 1, x2, y2};
            }
        }

        // Should never happen.
        return {1, 1, 1, 3};
    }

    void solve() {
        cin >> n;

        vector<vector<int>> even(n + 1, vector<int>(n + 1, -1));
        vector<vector<int>> odd(n + 1, vector<int>(n + 1, -1));

        bfsFill(even, 1, 1, 1);
        bfsFill(odd, 1, 2, 0);

        vector<vector<int>> g0(n + 1, vector<int>(n + 1, 0));
        vector<vector<int>> g1(n + 1, vector<int>(n + 1, 0));
        for (int i = 1; i <= n; i++) {
            for (int j = 1; j <= n; j++) {
                if (((i + j) & 1) == 0) {
                    g0[i][j] = even[i][j];
                    g1[i][j] = even[i][j];
                } else {
                    g0[i][j] = odd[i][j];
                    g1[i][j] = odd[i][j] ^ 1;
                }
            }
        }

        Query q = findDifference(g0, g1);
        bool p0 = existPal(g0, q.x1, q.y1, q.x2, q.y2);
        int r = ask(q.x1, q.y1, q.x2, q.y2);
        bool choose0 = (r == (p0 ? 1 : 0));
        const auto &ans = choose0 ? g0 : g1;

        cout << "!\n";
        for (int i = 1; i <= n; i++) {
            string s;
            s.reserve(n);
            for (int j = 1; j <= n; j++) s.push_back(char('0' + ans[i][j]));
            cout << s << "\n";
        }
        cout.flush();
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    Solver s;
    s.solve();
    return 0;
}