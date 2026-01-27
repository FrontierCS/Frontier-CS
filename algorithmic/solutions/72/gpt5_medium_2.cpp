#include <bits/stdc++.h>
using namespace std;

struct Vehicle {
    bool horizontal; // true if horizontal, false if vertical
    int length;
    int fixed; // row if horizontal, column if vertical
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    const int N = 6;
    int board[N][N];
    int max_id = 0;
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            cin >> board[i][j];
            max_id = max(max_id, board[i][j]);
        }
    }
    int n = max_id;
    if (n == 0) {
        // No vehicles: trivial
        cout << 0 << " " << 0 << "\n";
        return 0;
    }
    
    vector<vector<pair<int,int>>> cells(n+1);
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            int id = board[i][j];
            if (id > 0) cells[id].push_back({i,j});
        }
    }
    
    vector<Vehicle> vehicles(n);
    vector<int> initPos(n, 0);
    for (int id = 1; id <= n; ++id) {
        auto &v = vehicles[id-1];
        auto &c = cells[id];
        int len = (int)c.size();
        v.length = len;
        if (len == 0) { // should not happen, but guard
            v.horizontal = true;
            v.fixed = 0;
            initPos[id-1] = 0;
            continue;
        }
        // Determine orientation
        bool sameRow = true, sameCol = true;
        int r0 = c[0].first, c0 = c[0].second;
        int minr = r0, minc = c0;
        for (auto &p : c) {
            if (p.first != r0) sameRow = false;
            if (p.second != c0) sameCol = false;
            minr = min(minr, p.first);
            minc = min(minc, p.second);
        }
        if (sameRow) {
            v.horizontal = true;
            v.fixed = r0;
            initPos[id-1] = minc;
        } else if (sameCol) {
            v.horizontal = false;
            v.fixed = c0;
            initPos[id-1] = minr;
        } else {
            // invalid, but make a best guess
            // default to horizontal using min row's positions
            v.horizontal = true;
            v.fixed = r0;
            initPos[id-1] = minc;
        }
    }
    
    // Mixed radix base sizes
    vector<int> base(n);
    for (int i = 0; i < n; ++i) {
        base[i] = N - vehicles[i].length + 1; // positions along its movement axis
    }
    
    auto encode = [&](const vector<int>& pos)->long long {
        long long code = 0;
        long long mul = 1;
        for (int i = 0; i < n; ++i) {
            code += (long long)pos[i] * mul;
            mul *= base[i];
        }
        return code;
    };
    auto decode = [&](long long code)->vector<int> {
        vector<int> pos(n);
        for (int i = 0; i < n; ++i) {
            pos[i] = (int)(code % base[i]);
            code /= base[i];
        }
        return pos;
    };
    
    auto is_boundary_red = [&](const vector<int>& pos)->bool {
        // red car id = 1, index 0
        int Lr = vehicles[0].length; // should be 2
        return pos[0] == (N - Lr);
    };
    
    // Dijkstra
    unordered_map<long long, int> dist;
    dist.reserve(200000);
    dist.max_load_factor(0.7);
    using P = pair<int,long long>;
    priority_queue<P, vector<P>, greater<P>> pq;
    
    long long startCode = encode(initPos);
    dist[startCode] = 0;
    pq.push({0, startCode});
    
    int answer = -1;
    const int redExtra = vehicles[0].length; // steps to move completely out once at boundary
    while (!pq.empty()) {
        auto [d, code] = pq.top(); pq.pop();
        auto it = dist.find(code);
        if (it == dist.end() || it->second != d) continue;
        vector<int> pos = decode(code);
        if (is_boundary_red(pos)) {
            answer = d + redExtra;
            break;
        }
        // Build occupancy grid
        static int occ[N][N];
        for (int i = 0; i < N; ++i) for (int j = 0; j < N; ++j) occ[i][j] = 0;
        for (int i = 0; i < n; ++i) {
            int L = vehicles[i].length;
            if (vehicles[i].horizontal) {
                int r = vehicles[i].fixed;
                int c0 = pos[i];
                for (int k = 0; k < L; ++k) occ[r][c0 + k] = 1;
            } else {
                int c = vehicles[i].fixed;
                int r0 = pos[i];
                for (int k = 0; k < L; ++k) occ[r0 + k][c] = 1;
            }
        }
        // Generate neighbors
        for (int i = 0; i < n; ++i) {
            int L = vehicles[i].length;
            if (vehicles[i].horizontal) {
                int r = vehicles[i].fixed;
                int c0 = pos[i];
                // move left
                int t = c0 - 1, s = 0;
                while (t >= 0 && occ[r][t] == 0) { ++s; --t; }
                for (int step = 1; step <= s; ++step) {
                    vector<int> np = pos;
                    np[i] = c0 - step;
                    long long nc = encode(np);
                    int nd = d + step;
                    auto it2 = dist.find(nc);
                    if (it2 == dist.end() || nd < it2->second) {
                        dist[nc] = nd;
                        pq.push({nd, nc});
                    }
                }
                // move right
                t = c0 + L;
                s = 0;
                while (t < N && occ[r][t] == 0) { ++s; ++t; }
                for (int step = 1; step <= s; ++step) {
                    vector<int> np = pos;
                    np[i] = c0 + step;
                    long long nc = encode(np);
                    int nd = d + step;
                    auto it2 = dist.find(nc);
                    if (it2 == dist.end() || nd < it2->second) {
                        dist[nc] = nd;
                        pq.push({nd, nc});
                    }
                }
            } else {
                int c = vehicles[i].fixed;
                int r0 = pos[i];
                // move up
                int t = r0 - 1, s = 0;
                while (t >= 0 && occ[t][c] == 0) { ++s; --t; }
                for (int step = 1; step <= s; ++step) {
                    vector<int> np = pos;
                    np[i] = r0 - step;
                    long long nc = encode(np);
                    int nd = d + step;
                    auto it2 = dist.find(nc);
                    if (it2 == dist.end() || nd < it2->second) {
                        dist[nc] = nd;
                        pq.push({nd, nc});
                    }
                }
                // move down
                t = r0 + L;
                s = 0;
                while (t < N && occ[t][c] == 0) { ++s; ++t; }
                for (int step = 1; step <= s; ++step) {
                    vector<int> np = pos;
                    np[i] = r0 + step;
                    long long nc = encode(np);
                    int nd = d + step;
                    auto it2 = dist.find(nc);
                    if (it2 == dist.end() || nd < it2->second) {
                        dist[nc] = nd;
                        pq.push({nd, nc});
                    }
                }
            }
        }
    }
    
    if (answer < 0) answer = 0; // fallback, though guaranteed solvable
    
    cout << answer << " " << 0 << "\n";
    // No moves to form new puzzle
    return 0;
}