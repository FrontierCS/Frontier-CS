#include <bits/stdc++.h>
using namespace std;

struct Vehicle {
    int id;
    bool horizontal; // true: horizontal, false: vertical
    int len;         // 2 or 3
    int fixed;       // fixed row if horizontal, fixed col if vertical
};

struct VecHash {
    size_t operator()(const vector<int>& v) const noexcept {
        size_t h = 1469598103934665603ull;
        for (int x : v) {
            h ^= (size_t)(x + 0x9e3779b97f4a7c15ull);
            h *= 1099511628211ull;
        }
        return h;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    const int N = 6;
    vector<vector<int>> board(N, vector<int>(N));
    for (int r = 0; r < N; ++r) {
        for (int c = 0; c < N; ++c) {
            if (!(cin >> board[r][c])) return 0;
        }
    }

    int maxId = 0;
    for (int r = 0; r < N; ++r) for (int c = 0; c < N; ++c) maxId = max(maxId, board[r][c]);
    int n = maxId;
    if (n == 0) {
        // No vehicles; trivial
        cout << 0 << " " << 0 << "\n";
        return 0;
    }

    vector<vector<pair<int,int>>> cells(n+1);
    for (int r = 0; r < N; ++r) for (int c = 0; c < N; ++c) {
        int id = board[r][c];
        if (id > 0) cells[id].push_back({r,c});
    }

    vector<Vehicle> vehicles(n+1);
    vector<int> initPos(n+1, 0); // index by id, 1..n; store varying coordinate
    for (int id = 1; id <= n; ++id) {
        auto &v = vehicles[id];
        v.id = id;
        auto &cc = cells[id];
        int minr = 10, maxr = -1, minc = 10, maxc = -1;
        for (auto &p : cc) {
            minr = min(minr, p.first);
            maxr = max(maxr, p.first);
            minc = min(minc, p.second);
            maxc = max(maxc, p.second);
        }
        v.len = (int)cc.size();
        if (minr == maxr) {
            v.horizontal = true;
            v.fixed = minr;
            initPos[id] = minc; // min column
        } else {
            v.horizontal = false;
            v.fixed = minc;
            initPos[id] = minr; // min row
        }
    }

    // Build initial occupancy check if needed (not necessary)

    auto buildGrid = [&](const vector<int>& pos, int grid[6][6]) {
        for (int r=0;r<6;++r) for (int c=0;c<6;++c) grid[r][c]=0;
        for (int id=1; id<=n; ++id) {
            const auto &v = vehicles[id];
            if (v.horizontal) {
                int r = v.fixed;
                for (int k=0;k<v.len;++k) {
                    int c = pos[id] + k;
                    if (0 <= c && c < 6) grid[r][c] = id;
                }
            } else {
                int c = v.fixed;
                for (int k=0;k<v.len;++k) {
                    int r = pos[id] + k;
                    if (0 <= r && r < 6) grid[r][c] = id;
                }
            }
        }
    };

    auto isGoal = [&](const vector<int>& pos)->bool{
        // Red car is id 1; goal when its min_col == 6 (fully out)
        return vehicles[1].horizontal && pos[1] == 6;
    };

    vector<int> start(n+1);
    for (int i=1;i<=n;++i) start[i]=initPos[i];

    unordered_map<vector<int>, int, VecHash> dist;
    queue<vector<int>> q;
    dist[start]=0;
    q.push(start);

    int answer = -1;

    while (!q.empty()) {
        auto cur = q.front(); q.pop();
        int d = dist[cur];
        if (isGoal(cur)) {
            answer = d;
            break;
        }
        int grid[6][6];
        buildGrid(cur, grid);

        for (int id=1; id<=n; ++id) {
            const auto &v = vehicles[id];
            if (v.horizontal) {
                // move left
                if (cur[id] - 1 >= 0) {
                    int newLeft = cur[id] - 1;
                    int r = v.fixed;
                    int cEnter = newLeft; // entering left cell
                    if (grid[r][cEnter] == 0) {
                        auto nxt = cur;
                        nxt[id] = newLeft;
                        if (!dist.count(nxt)) {
                            dist[nxt] = d+1;
                            q.push(nxt);
                        }
                    }
                }
                // move right
                {
                    int newRightEdgeEnter = cur[id] + v.len; // column entering on right
                    bool can = true;
                    if (id == 1) {
                        // red car can move out to the right; if entering cell is on board, must be empty
                        if (newRightEdgeEnter < 6) {
                            int r = v.fixed, c = newRightEdgeEnter;
                            if (grid[r][c] != 0) can = false;
                        }
                        // Also allow move even if it goes beyond board; cap min_col at 6
                        if (can) {
                            auto nxt = cur;
                            nxt[id] = min(cur[id] + 1, 6); // clamp to 6 (fully out)
                            if (!dist.count(nxt)) {
                                dist[nxt] = d+1;
                                q.push(nxt);
                            }
                        }
                    } else {
                        if (cur[id] + v.len <= 5) { // ensure stays within board
                            int r = v.fixed, c = newRightEdgeEnter;
                            if (grid[r][c] == 0) {
                                auto nxt = cur;
                                nxt[id] = cur[id] + 1;
                                if (!dist.count(nxt)) {
                                    dist[nxt] = d+1;
                                    q.push(nxt);
                                }
                            }
                        }
                    }
                }
            } else {
                // vertical
                // move up
                if (cur[id] - 1 >= 0) {
                    int newTop = cur[id] - 1;
                    int c = v.fixed;
                    int rEnter = newTop;
                    if (grid[rEnter][c] == 0) {
                        auto nxt = cur;
                        nxt[id] = newTop;
                        if (!dist.count(nxt)) {
                            dist[nxt] = d+1;
                            q.push(nxt);
                        }
                    }
                }
                // move down
                if (cur[id] + v.len <= 5) {
                    int rEnter = cur[id] + v.len;
                    int c = v.fixed;
                    if (grid[rEnter][c] == 0) {
                        auto nxt = cur;
                        nxt[id] = cur[id] + 1;
                        if (!dist.count(nxt)) {
                            dist[nxt] = d+1;
                            q.push(nxt);
                        }
                    }
                }
            }
        }
    }

    if (answer < 0) answer = 0; // fallback, though guaranteed solvable

    // We choose to make 0 formation moves (stay with initial puzzle)
    cout << answer << " " << 0 << "\n";
    return 0;
}