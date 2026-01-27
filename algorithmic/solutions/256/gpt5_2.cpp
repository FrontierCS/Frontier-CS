#include <bits/stdc++.h>
using namespace std;

int n;

int ask(int x1, int y1, int x2, int y2) {
    cout << "? " << x1 << " " << y1 << " " << x2 << " " << y2 << endl;
    cout.flush();
    int r;
    if (!(cin >> r)) exit(0);
    if (r == -1) exit(0);
    return r;
}

bool existPalLen3(const vector<vector<int>>& g, int x1, int y1, int x2, int y2) {
    int dx = x2 - x1, dy = y2 - y1;
    // Only for dx+dy == 3
    if (dx + dy != 3) return false;
    auto val = [&](int x, int y){ return g[x][y]; };
    if (dx == 3 && dy == 0) {
        int a = val(x1, y1), b = val(x1+1, y1), c = val(x1+2, y1), d = val(x1+3, y1);
        return (a == d) && (b == c);
    }
    if (dx == 0 && dy == 3) {
        int a = val(x1, y1), b = val(x1, y1+1), c = val(x1, y1+2), d = val(x1, y1+3);
        return (a == d) && (b == c);
    }
    if (dx == 2 && dy == 1) {
        // R,R,D
        bool ok1 = (val(x1, y1) == val(x1+1, y1+1)) && (val(x1, y1+1) == val(x1, y1+2));
        // R,D,R
        bool ok2 = (val(x1, y1) == val(x1+1, y1+1)) && (val(x1, y1+1) == val(x1+1, y1));
        // D,R,R
        bool ok3 = (val(x1, y1) == val(x1+1, y1+1)) && (val(x1+1, y1) == val(x1+1, y1));
        // Note: last line had a typo; correct paths:
        ok1 = (val(x1, y1) == val(x1+1, y1+1)) && (val(x1, y1+1) == val(x1, y1+2));
        ok2 = (val(x1, y1) == val(x1+1, y1+1)) && (val(x1, y1+1) == val(x1+1, y1+1));
        ok3 = (val(x1, y1) == val(x1+1, y1+1)) && (val(x1+1, y1) == val(x1+1, y1+1));
        return ok1 || ok2 || ok3;
    }
    if (dx == 1 && dy == 2) {
        // D,D,R
        bool ok1 = (val(x1, y1) == val(x1+1, y1+2)) && (val(x1+1, y1) == val(x1+2, y1));
        // D,R,D
        bool ok2 = (val(x1, y1) == val(x1+1, y1+2)) && (val(x1+1, y1) == val(x1+1, y1+1));
        // R,D,D
        bool ok3 = (val(x1, y1) == val(x1+1, y1+2)) && (val(x1, y1+1) == val(x1+1, y1+1));
        // Correct paths enumeration:
        // R,R,D
        ok1 = (val(x1, y1) == val(x1+1, y1+2)) && (val(x1, y1+1) == val(x1, y1+2));
        // R,D,R
        ok2 = (val(x1, y1) == val(x1+1, y1+2)) && (val(x1, y1+1) == val(x1+1, y1+1));
        // D,R,R
        ok3 = (val(x1, y1) == val(x1+1, y1+2)) && (val(x1+1, y1) == val(x1+1, y1+1));
        return ok1 || ok2 || ok3;
    }
    return false;
}

bool existPalSmall(const vector<vector<int>>& g, int x1, int y1, int x2, int y2) {
    int dx = x2 - x1, dy = y2 - y1;
    int k = dx + dy;
    if (k == 3) return existPalLen3(g, x1, y1, x2, y2);
    // For safety, handle k==5 by enumerating all paths (up to 10).
    if (k == 5) {
        vector<string> seqs;
        int R = dy, D = dx;
        // generate all sequences of length 5 with R rights and D downs (R + D = 5)
        function<void(int,int,string)> gen = [&](int r, int d, string s){
            if ((int)s.size() == 5) {
                seqs.push_back(s);
                return;
            }
            if (r < R) gen(r+1, d, s + 'R');
            if (d < D) gen(r, d+1, s + 'D');
        };
        gen(0,0,"");
        for (auto &s : seqs) {
            int cx = x1, cy = y1;
            vector<int> vals;
            vals.push_back(g[cx][cy]);
            for (char c : s) {
                if (c == 'R') cy++;
                else cx++;
                vals.push_back(g[cx][cy]);
            }
            bool ok = true;
            for (int i = 0; i < 3; ++i) {
                if (vals[i] != vals[5 - i]) { ok = false; break; }
            }
            if (ok) return true;
        }
        return false;
    }
    return false;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    if (!(cin >> n)) return 0;

    vector<vector<int>> a(n+1, vector<int>(n+1, -1));

    // Even parity group from (1,1) known 1
    a[1][1] = 1;
    queue<pair<int,int>> q;
    q.push({1,1});
    auto inside = [&](int x, int y){ return 1 <= x && x <= n && 1 <= y && y <= n; };
    int dxs[3] = {2, 0, 1};
    int dys[3] = {0, 2, 1};
    while (!q.empty()) {
        auto [x, y] = q.front(); q.pop();
        for (int dir = 0; dir < 3; ++dir) {
            int nx = x + dxs[dir], ny = y + dys[dir];
            if (!inside(nx, ny)) continue;
            if (a[nx][ny] != -1) continue;
            int r = ask(x, y, nx, ny);
            a[nx][ny] = a[x][y] ^ (1 - r);
            q.push({nx, ny});
        }
    }

    // Odd parity group start from (1,2) assumed 0
    if (n >= 2) {
        a[1][2] = 0;
        q.push({1,2});
        while (!q.empty()) {
            auto [x, y] = q.front(); q.pop();
            for (int dir = 0; dir < 3; ++dir) {
                int nx = x + dxs[dir], ny = y + dys[dir];
                if (!inside(nx, ny)) continue;
                if (a[nx][ny] != -1) continue;
                int r = ask(x, y, nx, ny);
                a[nx][ny] = a[x][y] ^ (1 - r);
                q.push({nx, ny});
            }
        }
        // Fill remaining odd cells on y=1: (x,1) where x is even (since n is odd)
        for (int x = 2; x <= n-1; x += 2) {
            int y = 1;
            if (a[x][y] == -1) {
                // Use (x,1) to (x+1,2)
                int r = ask(x, y, x+1, 2);
                a[x][y] = a[x+1][2] ^ (1 - r);
            }
        }
    }

    // Now we have all cells filled up to a possible flip of odd parity cells.
    vector<vector<int>> B = a;
    vector<vector<int>> Bflip = a;
    for (int i = 1; i <= n; ++i)
        for (int j = 1; j <= n; ++j)
            if ((i + j) % 2 == 1)
                Bflip[i][j] ^= 1;

    // Find a pair with distance 3 where existence differs between B and Bflip
    int sx=-1, sy=-1, ex=-1, ey=-1;
    bool found = false;

    for (int i = 1; i <= n && !found; ++i) {
        for (int j = 1; j <= n && !found; ++j) {
            if (j + 3 <= n) {
                bool b1 = existPalLen3(B, i, j, i, j+3);
                bool b2 = existPalLen3(Bflip, i, j, i, j+3);
                if (b1 != b2) { sx=i; sy=j; ex=i; ey=j+3; found=true; break; }
            }
            if (i + 3 <= n) {
                bool b1 = existPalLen3(B, i, j, i+3, j);
                bool b2 = existPalLen3(Bflip, i, j, i+3, j);
                if (b1 != b2) { sx=i; sy=j; ex=i+3; ey=j; found=true; break; }
            }
            if (i + 2 <= n && j + 1 <= n) {
                bool b1 = existPalLen3(B, i, j, i+2, j+1);
                bool b2 = existPalLen3(Bflip, i, j, i+2, j+1);
                if (b1 != b2) { sx=i; sy=j; ex=i+2; ey=j+1; found=true; break; }
            }
            if (i + 1 <= n && j + 2 <= n) {
                bool b1 = existPalLen3(B, i, j, i+1, j+2);
                bool b2 = existPalLen3(Bflip, i, j, i+1, j+2);
                if (b1 != b2) { sx=i; sy=j; ex=i+1; ey=j+2; found=true; break; }
            }
        }
    }

    // As a rare fallback, try distance 5
    if (!found) {
        for (int i = 1; i <= n && !found; ++i) {
            for (int j = 1; j <= n && !found; ++j) {
                if (j + 5 <= n) {
                    bool b1 = existPalSmall(B, i, j, i, j+5);
                    bool b2 = existPalSmall(Bflip, i, j, i, j+5);
                    if (b1 != b2) { sx=i; sy=j; ex=i; ey=j+5; found=true; break; }
                }
                if (i + 5 <= n) {
                    bool b1 = existPalSmall(B, i, j, i+5, j);
                    bool b2 = existPalSmall(Bflip, i, j, i+5, j);
                    if (b1 != b2) { sx=i; sy=j; ex=i+5; ey=j; found=true; break; }
                }
                if (i + 4 <= n && j + 1 <= n) {
                    bool b1 = existPalSmall(B, i, j, i+4, j+1);
                    bool b2 = existPalSmall(Bflip, i, j, i+4, j+1);
                    if (b1 != b2) { sx=i; sy=j; ex=i+4; ey=j+1; found=true; break; }
                }
                if (i + 1 <= n && j + 4 <= n) {
                    bool b1 = existPalSmall(B, i, j, i+1, j+4);
                    bool b2 = existPalSmall(Bflip, i, j, i+1, j+4);
                    if (b1 != b2) { sx=i; sy=j; ex=i+1; ey=j+4; found=true; break; }
                }
                if (i + 3 <= n && j + 2 <= n) {
                    bool b1 = existPalSmall(B, i, j, i+3, j+2);
                    bool b2 = existPalSmall(Bflip, i, j, i+3, j+2);
                    if (b1 != b2) { sx=i; sy=j; ex=i+3; ey=j+2; found=true; break; }
                }
                if (i + 2 <= n && j + 3 <= n) {
                    bool b1 = existPalSmall(B, i, j, i+2, j+3);
                    bool b2 = existPalSmall(Bflip, i, j, i+2, j+3);
                    if (b1 != b2) { sx=i; sy=j; ex=i+2; ey=j+3; found=true; break; }
                }
            }
        }
    }

    bool useFlip = false;
    if (found) {
        // Ask judge for this pair
        int r = ask(sx, sy, ex, ey);
        bool pred = false, predFlip = false;
        int k = (ex - sx) + (ey - sy);
        if (k == 3) {
            pred = existPalLen3(B, sx, sy, ex, ey);
            predFlip = existPalLen3(Bflip, sx, sy, ex, ey);
        } else {
            pred = existPalSmall(B, sx, sy, ex, ey);
            predFlip = existPalSmall(Bflip, sx, sy, ex, ey);
        }
        // If judge's answer matches flip version, we need to flip odd cells
        if (r == (predFlip ? 1 : 0) && r != (pred ? 1 : 0)) {
            useFlip = true;
        } else {
            useFlip = false;
        }
    } else {
        // As a last resort, default to no flip
        useFlip = false;
    }

    if (useFlip) {
        for (int i = 1; i <= n; ++i)
            for (int j = 1; j <= n; ++j)
                if ((i + j) % 2 == 1)
                    a[i][j] ^= 1;
    }

    cout << "!" << endl;
    for (int i = 1; i <= n; ++i) {
        for (int j = 1; j <= n; ++j) cout << a[i][j];
        cout << endl;
    }
    cout.flush();
    return 0;
}