#include <bits/stdc++.h>
using namespace std;

static const int T = 3000;

static inline long long key(int x, int y) {
    return (static_cast<long long>(x) << 12) ^ static_cast<long long>(y);
}

static inline bool inRange(int x, int y) {
    return (1 <= x && x <= T && 1 <= y && y <= T);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int sx, sy;
    if (!(cin >> sx >> sy)) return 0;

    int rx = sx, ry = sy;
    int prx = rx, pry = ry;

    unordered_set<long long> painted;
    painted.reserve(1 << 20);
    painted.max_load_factor(0.7f);

    auto already = [&](int x, int y) -> bool {
        return painted.find(key(x, y)) != painted.end();
    };

    auto mark = [&](int x, int y) {
        if (!inRange(x, y)) x = 1, y = 1;
        painted.insert(key(x, y));
        cout << x << ' ' << y << '\n';
        cout.flush();
    };

    for (int turn = 1; turn <= T; turn++) {
        pair<int,int> mv = {1, 1};

        // Boundary trap attempts (y == 1 or x == 1), try to complete neighborhood.
        vector<pair<int,int>> trap;

        if (rx == 1 && ry == 1) {
            trap = {{1,2},{2,1},{2,2}};
        } else if (ry == 1) {
            trap = {{rx-1,1},{rx+1,1},{rx-1,2},{rx,2},{rx+1,2}};
        } else if (rx == 1) {
            trap = {{1,ry-1},{1,ry+1},{2,ry-1},{2,ry},{2,ry+1}};
        }

        bool chose = false;
        if (!trap.empty()) {
            // Prefer painting cells that complete the trap fastest: paint row/col neighbors first, then diagonals.
            auto scoreTrap = [&](const pair<int,int>& p) -> int {
                int x = p.first, y = p.second;
                if (!(x > 0 && y > 0) || !inRange(x,y)) return -1e9;
                int sc = 0;
                // prefer closer to robot
                sc -= (abs(x - rx) + abs(y - ry)) * 10;
                // prefer y=2 (for y==1 traps) or x=2 (for x==1 traps)
                if (ry == 1 && y == 2) sc += 50;
                if (rx == 1 && x == 2) sc += 50;
                // prefer unpainted
                if (!already(x, y)) sc += 1000;
                return sc;
            };
            sort(trap.begin(), trap.end(), [&](auto a, auto b){
                return scoreTrap(a) > scoreTrap(b);
            });
            for (auto [x,y] : trap) {
                if (!inRange(x,y)) continue;
                if (!already(x,y)) {
                    mv = {x,y};
                    chose = true;
                    break;
                }
            }
            if (!chose) {
                // If all are already painted, pick one (still valid); explosion should happen if fully surrounded.
                for (auto [x,y] : trap) {
                    if (inRange(x,y)) { mv = {x,y}; chose = true; break; }
                }
            }
        }

        if (!chose) {
            // General heuristic: paint the neighbor that most increases distance from origin (block outward move).
            // If all neighbors already painted/out of range, paint current cell if possible, else (1,1).
            long long bestScore = LLONG_MIN;
            pair<int,int> best = {1,1};

            for (int dx = -1; dx <= 1; dx++) {
                for (int dy = -1; dy <= 1; dy++) {
                    if (dx == 0 && dy == 0) continue;
                    int nx = rx + dx, ny = ry + dy;
                    if (nx <= 0 || ny <= 0) continue;
                    if (!inRange(nx, ny)) continue;
                    // Score: block moves that go far (prefer higher x+y).
                    long long sc = 0;
                    sc += 1000000LL * (nx + ny);
                    sc += 1000LL * nx + ny;
                    if (already(nx, ny)) sc -= 5000000000LL; // prefer unpainted
                    // Also try to counter last movement direction by blocking continuation
                    int ldx = rx - prx, ldy = ry - pry;
                    if (ldx != 0 || ldy != 0) {
                        if (nx == rx + ldx && ny == ry + ldy) sc += 2000000LL;
                    }
                    if (sc > bestScore) {
                        bestScore = sc;
                        best = {nx, ny};
                    }
                }
            }

            // Fallback: paint current cell (prevents revisiting).
            if (bestScore == LLONG_MIN) {
                if (inRange(rx, ry)) best = {rx, ry};
            }

            mv = best;
        }

        mark(mv.first, mv.second);

        prx = rx; pry = ry;

        int nx, ny;
        if (!(cin >> nx >> ny)) return 0;
        if (nx == 0 && ny == 0) return 0;
        rx = nx; ry = ny;
    }

    return 0;
}