#include <bits/stdc++.h>
using namespace std;

int n, m, k;
vector<string> init, target;
struct Op {
    int op, x, y;
};
vector<Op> moves;

void add_swap(int x1, int y1, int x2, int y2) {
    // adjacent swap: (x1,y1) and (x2,y2) must be adjacent
    if (x1 == x2) {
        if (y1 < y2) moves.push_back({-1, x1+1, y1+1}); // swap right
        else moves.push_back({-2, x1+1, y1+1}); // swap left
    } else {
        if (x1 < x2) moves.push_back({-4, x1+1, y1+1}); // swap down
        else moves.push_back({-3, x1+1, y1+1}); // swap up
    }
}

void apply_swap(vector<string>& grid, int x1, int y1, int x2, int y2) {
    swap(grid[x1][y1], grid[x2][y2]);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    cin >> n >> m >> k;
    init.resize(n);
    for (int i = 0; i < n; i++) cin >> init[i];
    string line;
    getline(cin, line); // consume newline after last init line
    getline(cin, line); // read empty line
    target.resize(n);
    for (int i = 0; i < n; i++) cin >> target[i];
    // read k presets (ignored)
    for (int i = 0; i < k; i++) {
        int np, mp;
        cin >> np >> mp;
        for (int j = 0; j < np; j++) cin >> line;
    }
    // check frequencies
    map<char, int> freq_init, freq_target;
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < m; j++) {
            freq_init[init[i][j]]++;
            freq_target[target[i][j]]++;
        }
    }
    if (freq_init != freq_target) {
        cout << -1 << endl;
        return 0;
    }
    // current grid
    vector<string> grid = init;
    int N = n * m;
    // process cells from last to first
    for (int p = N-1; p >= 0; p--) {
        int i = p / m;
        int j = p % m;
        if (grid[i][j] == target[i][j]) continue;
        // find a cell with index <= p that has target[i][j]
        int found = -1;
        int ri, rj;
        for (int q = 0; q <= p; q++) {
            int qi = q / m;
            int qj = q % m;
            if (grid[qi][qj] == target[i][j]) {
                found = q;
                ri = qi;
                rj = qj;
                break;
            }
        }
        assert(found != -1);
        // BFS to find path from (ri,rj) to (i,j) using only cells with index <= p
        vector<vector<int>> dist(n, vector<int>(m, -1));
        vector<vector<pair<int,int>>> prev(n, vector<pair<int,int>>(m, {-1,-1}));
        queue<pair<int,int>> qq;
        dist[ri][rj] = 0;
        qq.push({ri, rj});
        int di[] = {0,0,1,-1};
        int dj[] = {1,-1,0,0};
        while (!qq.empty()) {
            auto [x,y] = qq.front(); qq.pop();
            if (x == i && y == j) break;
            for (int d = 0; d < 4; d++) {
                int nx = x + di[d];
                int ny = y + dj[d];
                if (nx < 0 || nx >= n || ny < 0 || ny >= m) continue;
                if (dist[nx][ny] != -1) continue;
                int idx = nx * m + ny;
                if (idx > p) continue; // cannot go through fixed cells
                dist[nx][ny] = dist[x][y] + 1;
                prev[nx][ny] = {x,y};
                qq.push({nx, ny});
            }
        }
        // reconstruct path from (i,j) back to (ri,rj)
        vector<pair<int,int>> path;
        int x = i, y = j;
        while (x != ri || y != rj) {
            path.push_back({x,y});
            auto [px,py] = prev[x][y];
            x = px, y = py;
        }
        path.push_back({ri,rj});
        reverse(path.begin(), path.end()); // now from (ri,rj) to (i,j)
        // move the character along the path by swapping adjacent pairs
        for (size_t t = 0; t+1 < path.size(); t++) {
            int x1 = path[t].first, y1 = path[t].second;
            int x2 = path[t+1].first, y2 = path[t+1].second;
            add_swap(x1, y1, x2, y2);
            apply_swap(grid, x1, y1, x2, y2);
        }
        // now grid[i][j] should be target[i][j]
    }
    // output moves
    cout << moves.size() << "\n";
    for (auto& op : moves) {
        cout << op.op << " " << op.x << " " << op.y << "\n";
    }
    return 0;
}