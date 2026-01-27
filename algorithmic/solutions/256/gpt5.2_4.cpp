#include <bits/stdc++.h>
using namespace std;

static int n;

static int ask(int x1, int y1, int x2, int y2) {
    cout << "? " << x1 << " " << y1 << " " << x2 << " " << y2 << "\n";
    cout.flush();
    int r;
    if (!(cin >> r)) exit(0);
    if (r == -1) exit(0);
    return r;
}

static void fillParity(vector<vector<int>> &a, int parity, int sx, int sy, int sVal) {
    static const int dxs[6] = { 2, 0, 1, -2,  0, -1 };
    static const int dys[6] = { 0, 2, 1,  0, -2, -1 };

    queue<pair<int,int>> q;
    a[sx][sy] = sVal;
    q.push({sx, sy});

    while (!q.empty()) {
        auto [x, y] = q.front();
        q.pop();
        for (int t = 0; t < 6; t++) {
            int nx = x + dxs[t], ny = y + dys[t];
            if (nx < 1 || nx > n || ny < 1 || ny > n) continue;
            if (((nx + ny) & 1) != parity) continue;
            if (a[nx][ny] != -1) continue;

            int ax = x, ay = y, bx = nx, by = ny;
            if (!(ax <= bx && ay <= by)) {
                swap(ax, bx);
                swap(ay, by);
            }
            int eq = ask(ax, ay, bx, by); // for dist=2: eq==1 iff values equal
            a[nx][ny] = a[x][y] ^ (eq ? 0 : 1);
            q.push({nx, ny});
        }
    }
}

static bool existsPalBruteSmall(const vector<vector<int>> &g, int x1, int y1, int x2, int y2) {
    int dx = x2 - x1, dy = y2 - y1;
    int d = dx + dy;
    int seq[64];
    bool found = false;

    function<void(int,int,int,int,int)> dfs = [&](int x, int y, int dxr, int dyr, int depth) {
        if (found) return;
        seq[depth] = g[x][y];
        if (dxr == 0 && dyr == 0) {
            for (int i = 0; i <= depth; i++) {
                if (seq[i] != seq[depth - i]) return;
            }
            found = true;
            return;
        }
        if (dxr > 0) dfs(x + 1, y, dxr - 1, dyr, depth + 1);
        if (dyr > 0) dfs(x, y + 1, dxr, dyr - 1, depth + 1);
    };

    dfs(x1, y1, dx, dy, 0);
    return found;
}

static bool existsPalDP(const vector<vector<int>> &g, int x1, int y1, int x2, int y2) {
    int dx = x2 - x1, dy = y2 - y1;
    int d = dx + dy;
    if (g[x1][y1] != g[x2][y2]) return false;

    int steps = d / 2;
    int H = dx + 1;

    vector<vector<unsigned char>> dp(H, vector<unsigned char>(H, 0)), ndp(H, vector<unsigned char>(H, 0));
    dp[0][dx] = 1;

    for (int k = 0; k < steps; k++) {
        for (int i = 0; i < H; i++) memset(ndp[i].data(), 0, H);

        int ssum = x1 + y1 + k;
        int esum = x2 + y2 - k;

        for (int a = 0; a <= dx; a++) {
            int xs = x1 + a;
            int ys = ssum - xs;
            if (ys < y1 || ys > y2) continue;

            for (int b = 0; b <= dx; b++) {
                if (!dp[a][b]) continue;
                int xe = x1 + b;
                int ye = esum - xe;
                if (ye < y1 || ye > y2) continue;

                // start moves: right or down; end moves (reverse): left or up
                for (int ms = 0; ms < 2; ms++) {
                    int xs2 = xs + (ms == 1);
                    int ys2 = ys + (ms == 0);
                    if (xs2 < x1 || xs2 > x2 || ys2 < y1 || ys2 > y2) continue;
                    int a2 = xs2 - x1;

                    for (int me = 0; me < 2; me++) {
                        int xe2 = xe - (me == 1); // up
                        int ye2 = ye - (me == 0); // left
                        if (xe2 < x1 || xe2 > x2 || ye2 < y1 || ye2 > y2) continue;
                        int b2 = xe2 - x1;

                        if (g[xs2][ys2] == g[xe2][ye2]) ndp[a2][b2] = 1;
                    }
                }
            }
        }
        dp.swap(ndp);
    }

    int ssum = x1 + y1 + steps;
    int esum = x2 + y2 - steps;
    int want = d & 1;

    for (int a = 0; a <= dx; a++) {
        int xs = x1 + a;
        int ys = ssum - xs;
        if (ys < y1 || ys > y2) continue;
        for (int b = 0; b <= dx; b++) {
            if (!dp[a][b]) continue;
            int xe = x1 + b;
            int ye = esum - xe;
            if (ye < y1 || ye > y2) continue;
            if (abs(xs - xe) + abs(ys - ye) == want) return true;
        }
    }
    return false;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    cin >> n;

    vector<vector<int>> evenRel(n + 1, vector<int>(n + 1, -1));
    vector<vector<int>> oddRel(n + 1, vector<int>(n + 1, -1));

    // Fill even parity absolutely: (1,1)=1
    fillParity(evenRel, 0, 1, 1, 1);

    // Fill odd parity relatively: assume (1,2)=0
    fillParity(oddRel, 1, 1, 2, 0);

    vector<vector<int>> g1(n + 1, vector<int>(n + 1, 0));
    vector<vector<int>> g2(n + 1, vector<int>(n + 1, 0));

    for (int i = 1; i <= n; i++) {
        for (int j = 1; j <= n; j++) {
            if (((i + j) & 1) == 0) {
                g1[i][j] = evenRel[i][j];
                g2[i][j] = evenRel[i][j];
            } else {
                g1[i][j] = oddRel[i][j];
                g2[i][j] = oddRel[i][j] ^ 1;
            }
        }
    }

    // Find a distinguishing query
    int qx1 = -1, qy1 = -1, qx2 = -1, qy2 = -1;
    bool p1 = false, p2 = false;

    for (int d = 3; d <= 11 && qx1 == -1; d += 2) {
        for (int dx = 0; dx <= d && qx1 == -1; dx++) {
            int dy = d - dx;
            for (int x1 = 1; x1 + dx <= n && qx1 == -1; x1++) {
                for (int y1 = 1; y1 + dy <= n && qx1 == -1; y1++) {
                    int x2 = x1 + dx, y2 = y1 + dy;
                    if ((x1 + y1 + 2) > (x2 + y2)) continue; // should not happen for d>=2
                    if (((x1 + y1) & 1) == ((x2 + y2) & 1)) continue; // need opposite parity to differ

                    bool a1 = existsPalBruteSmall(g1, x1, y1, x2, y2);
                    bool a2 = existsPalBruteSmall(g2, x1, y1, x2, y2);
                    if (a1 != a2) {
                        qx1 = x1; qy1 = y1; qx2 = x2; qy2 = y2;
                        p1 = a1; p2 = a2;
                    }
                }
            }
        }
    }

    if (qx1 == -1) {
        // Deterministic candidates
        vector<array<int,4>> candidates = {
            {1, 1, n, n-1},
            {1, 2, n, n},
            {1, 1, n-1, n},
            {2, 1, n, n},
            {1, 1, 2, n},
            {1, 1, n, 2}
        };
        for (auto c : candidates) {
            int x1=c[0], y1=c[1], x2=c[2], y2=c[3];
            if (x1<1||y1<1||x2>n||y2>n||x1>x2||y1>y2) continue;
            if (x1 + y1 + 2 > x2 + y2) continue;
            if (((x1 + y1) & 1) == ((x2 + y2) & 1)) continue;
            bool a1 = existsPalDP(g1, x1, y1, x2, y2);
            bool a2 = existsPalDP(g2, x1, y1, x2, y2);
            if (a1 != a2) {
                qx1=x1; qy1=y1; qx2=x2; qy2=y2;
                p1=a1; p2=a2;
                break;
            }
        }
    }

    if (qx1 == -1) {
        // Random fallback
        mt19937 rng((uint32_t)chrono::steady_clock::now().time_since_epoch().count());
        for (int it = 0; it < 250 && qx1 == -1; it++) {
            int x1 = uniform_int_distribution<int>(1, n)(rng);
            int y1 = uniform_int_distribution<int>(1, n)(rng);
            int x2 = uniform_int_distribution<int>(x1, n)(rng);
            int y2 = uniform_int_distribution<int>(y1, n)(rng);
            if (x1 == x2 && y1 == y2) continue;
            if (x1 + y1 + 2 > x2 + y2) continue;
            if (((x1 + y1) & 1) == ((x2 + y2) & 1)) continue;
            bool a1 = existsPalDP(g1, x1, y1, x2, y2);
            bool a2 = existsPalDP(g2, x1, y1, x2, y2);
            if (a1 != a2) {
                qx1=x1; qy1=y1; qx2=x2; qy2=y2;
                p1=a1; p2=a2;
                break;
            }
        }
    }

    // If still not found, assume g1 (should not happen in valid interactive setting)
    const vector<vector<int>> *ansGrid = &g1;

    if (qx1 != -1) {
        int real = ask(qx1, qy1, qx2, qy2);
        if (real == (int)p1) ansGrid = &g1;
        else ansGrid = &g2;
    }

    cout << "!\n";
    for (int i = 1; i <= n; i++) {
        string s;
        s.reserve(n);
        for (int j = 1; j <= n; j++) s.push_back(char('0' + (*ansGrid)[i][j]));
        cout << s << "\n";
    }
    cout.flush();
    return 0;
}