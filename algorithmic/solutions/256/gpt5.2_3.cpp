#include <bits/stdc++.h>
using namespace std;

static const int N = 50;
static vector<int> mark4d;
static int stamp4d = 1;

static inline int idx4(int ux, int uy, int vx, int vy) {
    return (((ux * N + uy) * N + vx) * N + vy);
}

static int n;

static int ask(int x1, int y1, int x2, int y2) {
    if (x1 > x2 || y1 > y2) {
        swap(x1, x2);
        swap(y1, y2);
    }
    cout << "? " << x1 << " " << y1 << " " << x2 << " " << y2 << "\n";
    cout.flush();
    int r;
    if (!(cin >> r)) exit(0);
    if (r == -1) exit(0);
    return r;
}

static void fillParity(vector<vector<int>>& a, int sx, int sy, int val) {
    static const int dxs[6] = {2, -2, 0, 0, 1, -1};
    static const int dys[6] = {0, 0, 2, -2, 1, -1};

    int p = (sx + sy) & 1;
    queue<pair<int,int>> q;
    a[sx][sy] = val;
    q.push({sx, sy});

    while (!q.empty()) {
        auto [x, y] = q.front();
        q.pop();
        for (int k = 0; k < 6; k++) {
            int nx = x + dxs[k], ny = y + dys[k];
            if (nx < 1 || nx > n || ny < 1 || ny > n) continue;
            if (((nx + ny) & 1) != p) continue;
            if (a[nx][ny] != -1) continue;
            int r = ask(x, y, nx, ny); // 1 => equal, 0 => different
            a[nx][ny] = a[x][y] ^ (1 - r);
            q.push({nx, ny});
        }
    }
}

static bool bruteExists(const vector<vector<int>>& b, int x1, int y1, int x2, int y2) {
    int dx = x2 - x1, dy = y2 - y1;
    int d = dx + dy;
    vector<int> seq(d + 1);

    function<bool(int,int,int,int)> rec = [&](int x, int y, int pos, int downs) -> bool {
        seq[pos] = b[x][y];
        if (pos == d) {
            for (int l = 0, r = d; l < r; l++, r--) {
                if (seq[l] != seq[r]) return false;
            }
            return true;
        }
        int rights = pos - downs;
        if (downs < dx) {
            if (rec(x + 1, y, pos + 1, downs + 1)) return true;
        }
        if (rights < dy) {
            if (rec(x, y + 1, pos + 1, downs)) return true;
        }
        return false;
    };

    return rec(x1, y1, 0, 0);
}

static bool dpExists(const vector<vector<int>>& b, int x1, int y1, int x2, int y2) {
    int dx = x2 - x1, dy = y2 - y1;
    int d = dx + dy;

    if (d < 2) return false;
    if (b[x1][y1] != b[x2][y2]) return false;

    vector<array<short,4>> cur, nxt;
    cur.push_back({(short)x1, (short)y1, (short)x2, (short)y2});

    int layers = d / 2;

    for (int step = 0; step < layers; step++) {
        stamp4d++;
        if (stamp4d == INT_MAX) {
            fill(mark4d.begin(), mark4d.end(), 0);
            stamp4d = 1;
        }
        nxt.clear();
        for (auto st : cur) {
            int ux = st[0], uy = st[1], vx = st[2], vy = st[3];

            int umx[2] = {ux + 1, ux};
            int umy[2] = {uy, uy + 1};
            int vmx[2] = {vx - 1, vx};
            int vmy[2] = {vy, vy - 1};

            for (int ui = 0; ui < 2; ui++) {
                int nux = umx[ui], nuy = umy[ui];
                if (nux < x1 || nux > x2 || nuy < y1 || nuy > y2) continue;
                for (int vi = 0; vi < 2; vi++) {
                    int nvx = vmx[vi], nvy = vmy[vi];
                    if (nvx < x1 || nvx > x2 || nvy < y1 || nvy > y2) continue;
                    if (nux > nvx || nuy > nvy) continue;
                    if (b[nux][nuy] != b[nvx][nvy]) continue;
                    int id = idx4(nux, nuy, nvx, nvy);
                    if (mark4d[id] == stamp4d) continue;
                    mark4d[id] = stamp4d;
                    nxt.push_back({(short)nux, (short)nuy, (short)nvx, (short)nvy});
                }
            }
        }
        cur.swap(nxt);
        if (cur.empty()) return false;
    }

    if ((d & 1) == 0) {
        for (auto st : cur) {
            if (st[0] == st[2] && st[1] == st[3]) return true;
        }
        return false;
    } else {
        for (auto st : cur) {
            int ux = st[0], uy = st[1], vx = st[2], vy = st[3];
            if ((ux == vx && uy + 1 == vy) || (ux + 1 == vx && uy == vy)) return true;
        }
        return false;
    }
}

static bool palRow(const vector<vector<int>>& b, int x, int y1, int y2) {
    while (y1 < y2) {
        if (b[x][y1] != b[x][y2]) return false;
        y1++; y2--;
    }
    return true;
}

static bool palCol(const vector<vector<int>>& b, int x1, int x2, int y) {
    while (x1 < x2) {
        if (b[x1][y] != b[x2][y]) return false;
        x1++; x2--;
    }
    return true;
}

struct Discrim {
    int x1, y1, x2, y2;
    bool p1, p2;
    bool ok = false;
};

static Discrim findDiscriminating(const vector<vector<int>>& b1, const vector<vector<int>>& b2) {
    Discrim res;

    // Phase A: all pairs with distance 3 (very small, brute enumeration <= 3 paths)
    {
        int d = 3;
        for (int dx = 0; dx <= d; dx++) {
            int dy = d - dx;
            for (int x1 = 1; x1 + dx <= n; x1++) {
                for (int y1 = 1; y1 + dy <= n; y1++) {
                    int x2 = x1 + dx, y2 = y1 + dy;
                    bool p1 = bruteExists(b1, x1, y1, x2, y2);
                    bool p2 = bruteExists(b2, x1, y1, x2, y2);
                    if (p1 != p2) {
                        res = {x1, y1, x2, y2, p1, p2, true};
                        return res;
                    }
                }
            }
        }
    }

    // Phase B: straight segments (unique path), scan varying lengths
    for (int len = 2; len <= n - 1; len++) {
        // Horizontal
        for (int i = 1; i <= n; i++) {
            for (int j = 1; j + len <= n; j++) {
                bool p1 = palRow(b1, i, j, j + len);
                bool p2 = palRow(b2, i, j, j + len);
                if (p1 != p2) {
                    res = {i, j, i, j + len, p1, p2, true};
                    return res;
                }
            }
        }
        // Vertical
        for (int j = 1; j <= n; j++) {
            for (int i = 1; i + len <= n; i++) {
                bool p1 = palCol(b1, i, i + len, j);
                bool p2 = palCol(b2, i, i + len, j);
                if (p1 != p2) {
                    res = {i, j, i + len, j, p1, p2, true};
                    return res;
                }
            }
        }
    }

    // Phase C: random DP search (general)
    {
        std::mt19937 rng(712367 + n * 911);
        for (int it = 0; it < 600; it++) {
            int x1 = (int)(rng() % n) + 1;
            int y1 = (int)(rng() % n) + 1;
            int x2 = (int)(rng() % (n - x1 + 1)) + x1;
            int y2 = (int)(rng() % (n - y1 + 1)) + y1;
            if (x1 == x2 && y1 == y2) continue;
            int d = (x2 - x1) + (y2 - y1);
            if (d < 2) continue;
            if (((x1 + y1) & 1) == ((x2 + y2) & 1) && (rng() & 1)) continue;

            bool p1 = dpExists(b1, x1, y1, x2, y2);
            bool p2 = dpExists(b2, x1, y1, x2, y2);
            if (p1 != p2) {
                res = {x1, y1, x2, y2, p1, p2, true};
                return res;
            }
        }
    }

    // Phase D: deterministic DP scan from (1,1) to all ends
    {
        int x1 = 1, y1 = 1;
        for (int x2 = 1; x2 <= n; x2++) {
            for (int y2 = 1; y2 <= n; y2++) {
                int d = (x2 - x1) + (y2 - y1);
                if (x2 < x1 || y2 < y1 || d < 2) continue;
                bool p1 = dpExists(b1, x1, y1, x2, y2);
                bool p2 = dpExists(b2, x1, y1, x2, y2);
                if (p1 != p2) {
                    res = {x1, y1, x2, y2, p1, p2, true};
                    return res;
                }
            }
        }
    }

    return res;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    cin >> n;
    mark4d.assign(N * N * N * N, 0);

    vector<vector<int>> base(n + 1, vector<int>(n + 1, -1));

    // Fill even parity from (1,1)=1
    fillParity(base, 1, 1, 1);

    // Fill odd parity relative to (1,2)=0
    fillParity(base, 1, 2, 0);

    vector<vector<int>> b1 = base;
    vector<vector<int>> b2 = base;
    for (int i = 1; i <= n; i++) {
        for (int j = 1; j <= n; j++) {
            if (((i + j) & 1) == 1) b2[i][j] = 1 - b2[i][j];
        }
    }

    Discrim d = findDiscriminating(b1, b2);
    vector<vector<int>> finalBoard = b1;

    if (d.ok) {
        int real = ask(d.x1, d.y1, d.x2, d.y2);
        bool chosenB1 = (real == (int)d.p1);
        bool chosenB2 = (real == (int)d.p2);
        if (chosenB1 && !chosenB2) finalBoard = b1;
        else if (chosenB2 && !chosenB1) finalBoard = b2;
        else finalBoard = chosenB1 ? b1 : b2; // should not happen if discriminating, but safe
    } else {
        // Fallback (should not happen): choose b1
        finalBoard = b1;
    }

    cout << "!\n";
    for (int i = 1; i <= n; i++) {
        for (int j = 1; j <= n; j++) cout << finalBoard[i][j];
        cout << "\n";
    }
    cout.flush();
    return 0;
}