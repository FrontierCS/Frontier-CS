#include <bits/stdc++.h>
using namespace std;

struct Vehicle {
    bool hor;   // true = horizontal
    int len;    // 2 or 3
    int fixed;  // row if hor, col if vertical
};

const int MAX_VEH = 10;
const int MAX_STATES = 500000;
const int INF = 1000000000;

int n;                  // number of vehicles
Vehicle veh[MAX_VEH+1]; // 1-based

uint64_t encode(const int pos[]) {
    uint64_t key = 0;
    for (int i = 1; i <= n; ++i) {
        key |= (uint64_t(pos[i]) << ((i - 1) * 3));
    }
    return key;
}

void decode(uint64_t key, int pos[]) {
    for (int i = 1; i <= n; ++i) {
        pos[i] = (int)((key >> ((i - 1) * 3)) & 7ULL);
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int board_in[6][6];
    int maxId = 0;
    for (int r = 0; r < 6; ++r) {
        for (int c = 0; c < 6; ++c) {
            if (!(cin >> board_in[r][c])) return 0;
            maxId = max(maxId, board_in[r][c]);
        }
    }
    n = maxId;

    vector<vector<pair<int,int>>> occ(n + 1);
    for (int r = 0; r < 6; ++r) {
        for (int c = 0; c < 6; ++c) {
            int id = board_in[r][c];
            if (id > 0) occ[id].push_back({r, c});
        }
    }

    // Determine vehicle orientation, length, fixed line
    for (int id = 1; id <= n; ++id) {
        auto &cells = occ[id];
        bool hor;
        if (cells.size() >= 2) {
            hor = (cells[0].first == cells[1].first);
        } else {
            // Fallback (should not happen per problem description)
            hor = true;
        }
        int minr = 6, maxr = -1, minc = 6, maxc = -1;
        for (auto &p : cells) {
            minr = min(minr, p.first);
            maxr = max(maxr, p.first);
            minc = min(minc, p.second);
            maxc = max(maxc, p.second);
        }
        int len = hor ? (maxc - minc + 1) : (maxr - minr + 1);
        veh[id].hor = hor;
        veh[id].len = len;
        veh[id].fixed = hor ? minr : minc;
    }

    // Initial positions
    int pos0[MAX_VEH + 1];
    for (int id = 1; id <= n; ++id) {
        auto &cells = occ[id];
        if (veh[id].hor) {
            int row = veh[id].fixed;
            int minc = 6;
            for (auto &p : cells) if (p.first == row) minc = min(minc, p.second);
            pos0[id] = minc;
        } else {
            int col = veh[id].fixed;
            int minr = 6;
            for (auto &p : cells) if (p.second == col) minr = min(minr, p.first);
            pos0[id] = minr;
        }
    }

    uint64_t key0 = encode(pos0);

    // BFS state enumeration
    unordered_map<uint64_t,int> mp;
    mp.reserve(1 << 20);
    mp.max_load_factor(0.7f);

    vector<uint64_t> keys;
    keys.reserve(MAX_STATES);
    vector<vector<int>> adj;
    adj.reserve(MAX_STATES);
    vector<int> parentState;
    parentState.reserve(MAX_STATES);
    vector<int> parentVid;
    parentVid.reserve(MAX_STATES);
    vector<char> parentDir;
    parentDir.reserve(MAX_STATES);
    vector<bool> terminal;
    terminal.reserve(MAX_STATES);
    vector<int> costExit;
    costExit.reserve(MAX_STATES);

    keys.push_back(key0);
    mp[key0] = 0;
    adj.emplace_back();
    parentState.push_back(-1);
    parentVid.push_back(-1);
    parentDir.push_back(0);
    terminal.push_back(false);
    costExit.push_back(0);

    vector<int> q;
    q.reserve(MAX_STATES);
    q.push_back(0);

    int curIndex = 0;
    int pos[MAX_VEH + 1];
    int board[6][6];

    while (curIndex < (int)q.size()) {
        int u = q[curIndex++];
        uint64_t key = keys[u];
        decode(key, pos);

        // Build board occupancy
        for (int r = 0; r < 6; ++r)
            for (int c = 0; c < 6; ++c)
                board[r][c] = 0;
        for (int id = 1; id <= n; ++id) {
            const Vehicle &v = veh[id];
            if (v.hor) {
                int r = v.fixed;
                for (int k = 0; k < v.len; ++k)
                    board[r][pos[id] + k] = id;
            } else {
                int c = v.fixed;
                for (int k = 0; k < v.len; ++k)
                    board[pos[id] + k][c] = id;
            }
        }

        // Determine if terminal for red car (id=1)
        bool term = false;
        int cost = INF;
        {
            const Vehicle &vr = veh[1];
            int rowR = vr.fixed;
            int right = pos[1] + vr.len - 1;
            bool ok = true;
            for (int c = right + 1; c < 6; ++c) {
                if (board[rowR][c] != 0) {
                    ok = false;
                    break;
                }
            }
            if (ok) {
                term = true;
                cost = 5 - right + vr.len;
            }
        }
        terminal[u] = term;
        costExit[u] = cost;

        // Generate neighbors
        for (int id = 1; id <= n; ++id) {
            const Vehicle &v = veh[id];
            if (v.hor) {
                int row = v.fixed;
                int left = pos[id];
                int right = pos[id] + v.len - 1;

                // Move left
                for (int step = 1; left - step >= 0 && board[row][left - step] == 0; ++step) {
                    pos[id] = left - step;
                    uint64_t nkey = encode(pos);
                    auto it = mp.find(nkey);
                    int vi;
                    if (it == mp.end()) {
                        if ((int)keys.size() >= MAX_STATES) {
                            pos[id] = left;
                            break;
                        }
                        vi = (int)keys.size();
                        mp.emplace(nkey, vi);
                        keys.push_back(nkey);
                        adj.emplace_back();
                        parentState.push_back(u);
                        parentVid.push_back(id);
                        parentDir.push_back('L');
                        terminal.push_back(false);
                        costExit.push_back(0);
                        q.push_back(vi);
                    } else {
                        vi = it->second;
                    }
                    adj[u].push_back(vi);
                    adj[vi].push_back(u);
                }
                pos[id] = left;

                // Move right
                for (int step = 1; right + step < 6 && board[row][right + step] == 0; ++step) {
                    pos[id] = left + step;
                    uint64_t nkey = encode(pos);
                    auto it = mp.find(nkey);
                    int vi;
                    if (it == mp.end()) {
                        if ((int)keys.size() >= MAX_STATES) {
                            pos[id] = left;
                            break;
                        }
                        vi = (int)keys.size();
                        mp.emplace(nkey, vi);
                        keys.push_back(nkey);
                        adj.emplace_back();
                        parentState.push_back(u);
                        parentVid.push_back(id);
                        parentDir.push_back('R');
                        terminal.push_back(false);
                        costExit.push_back(0);
                        q.push_back(vi);
                    } else {
                        vi = it->second;
                    }
                    adj[u].push_back(vi);
                    adj[vi].push_back(u);
                }
                pos[id] = left;
            } else {
                int col = v.fixed;
                int top = pos[id];
                int bottom = pos[id] + v.len - 1;

                // Move up
                for (int step = 1; top - step >= 0 && board[top - step][col] == 0; ++step) {
                    pos[id] = top - step;
                    uint64_t nkey = encode(pos);
                    auto it = mp.find(nkey);
                    int vi;
                    if (it == mp.end()) {
                        if ((int)keys.size() >= MAX_STATES) {
                            pos[id] = top;
                            break;
                        }
                        vi = (int)keys.size();
                        mp.emplace(nkey, vi);
                        keys.push_back(nkey);
                        adj.emplace_back();
                        parentState.push_back(u);
                        parentVid.push_back(id);
                        parentDir.push_back('U');
                        terminal.push_back(false);
                        costExit.push_back(0);
                        q.push_back(vi);
                    } else {
                        vi = it->second;
                    }
                    adj[u].push_back(vi);
                    adj[vi].push_back(u);
                }
                pos[id] = top;

                // Move down
                for (int step = 1; bottom + step < 6 && board[bottom + step][col] == 0; ++step) {
                    pos[id] = top + step;
                    uint64_t nkey = encode(pos);
                    auto it = mp.find(nkey);
                    int vi;
                    if (it == mp.end()) {
                        if ((int)keys.size() >= MAX_STATES) {
                            pos[id] = top;
                            break;
                        }
                        vi = (int)keys.size();
                        mp.emplace(nkey, vi);
                        keys.push_back(nkey);
                        adj.emplace_back();
                        parentState.push_back(u);
                        parentVid.push_back(id);
                        parentDir.push_back('D');
                        terminal.push_back(false);
                        costExit.push_back(0);
                        q.push_back(vi);
                    } else {
                        vi = it->second;
                    }
                    adj[u].push_back(vi);
                    adj[vi].push_back(u);
                }
                pos[id] = top;
            }
        }
    }

    int N = (int)keys.size();

    // Multi-source Dijkstra for distance to exit
    vector<int> dist(N, INF);
    using PII = pair<int,int>;
    priority_queue<PII, vector<PII>, greater<PII>> pq;
    for (int i = 0; i < N; ++i) {
        if (terminal[i]) {
            dist[i] = costExit[i];
            pq.emplace(dist[i], i);
        }
    }
    if (!pq.empty()) {
        while (!pq.empty()) {
            auto [d, u] = pq.top();
            pq.pop();
            if (d != dist[u]) continue;
            for (int v : adj[u]) {
                if (dist[v] > d + 1) {
                    dist[v] = d + 1;
                    pq.emplace(dist[v], v);
                }
            }
        }
    }

    // Choose best state
    int bestIdx = 0;
    int bestSteps = (dist[0] < INF ? dist[0] : 0);
    for (int i = 0; i < N; ++i) {
        if (dist[i] < INF && dist[i] > bestSteps) {
            bestSteps = dist[i];
            bestIdx = i;
        }
    }

    // Reconstruct sequence from initial (0) to bestIdx
    vector<pair<int,char>> seq;
    int cur = bestIdx;
    while (cur != 0 && cur != -1) {
        seq.push_back({parentVid[cur], parentDir[cur]});
        cur = parentState[cur];
    }
    reverse(seq.begin(), seq.end());

    int solveSteps = bestSteps;
    if (solveSteps < 0 || solveSteps >= INF) solveSteps = 0;

    cout << solveSteps << " " << seq.size() << "\n";
    for (auto &mv : seq) {
        cout << mv.first << " " << mv.second << "\n";
    }

    return 0;
}