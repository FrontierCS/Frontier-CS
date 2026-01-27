#include <bits/stdc++.h>
using namespace std;

struct Vehicle {
    bool horizontal; // true if horizontal, false if vertical
    int len;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    const int N = 6;
    vector<vector<int>> grid(N, vector<int>(N,0));
    int max_id = 0;
    for (int i=0;i<N;i++){
        for (int j=0;j<N;j++){
            int x; 
            if(!(cin>>x)) return 0;
            grid[i][j]=x;
            max_id = max(max_id, x);
        }
    }
    if (max_id == 0) {
        // No vehicles; trivial
        cout << 0 << " " << 0 << "\n";
        return 0;
    }
    int n = max_id;
    vector<Vehicle> info(n+1);
    vector<vector<pair<int,int>>> cells(n+1);
    for (int i=0;i<N;i++){
        for (int j=0;j<N;j++){
            int id = grid[i][j];
            if (id>0) cells[id].push_back({i,j});
        }
    }
    for (int id=1; id<=n; id++){
        if (cells[id].empty()) continue;
        // Determine orientation and length
        bool hori = false;
        if (cells[id].size() >= 2) {
            if (cells[id][0].first == cells[id][1].first) hori = true;
        } else {
            // Single cell shouldn't happen, but default horizontal
            hori = true;
        }
        info[id].horizontal = hori;
        info[id].len = (int)cells[id].size();
    }
    // Initial positions as top-left for each vehicle
    vector<pair<int,int>> init_pos(n+1, {-1,-1});
    for (int id=1; id<=n; id++){
        if (cells[id].empty()) continue;
        int minr = 10, minc = 10;
        for (auto &p: cells[id]) {
            minr = min(minr, p.first);
            minc = min(minc, p.second);
        }
        if (info[id].horizontal) {
            // same row; minc is leftmost, row is that row
            int row = cells[id][0].first;
            init_pos[id] = {row, minc};
        } else {
            // same column; minr is topmost, column is that column
            int col = cells[id][0].second;
            init_pos[id] = {minr, col};
        }
    }

    auto encode = [&](const vector<pair<int,int>>& pos)->string{
        string s;
        s.resize(n*2);
        for (int id=1; id<=n; id++){
            int r = pos[id].first, c = pos[id].second;
            char a = (char)(r);
            char b = (char)(c);
            s[(id-1)*2] = a;
            s[(id-1)*2+1] = b;
        }
        return s;
    };

    auto build_board = [&](const vector<pair<int,int>>& pos)->array<array<int,6>,6>{
        array<array<int,6>,6> b{};
        for (int i=0;i<6;i++) for (int j=0;j<6;j++) b[i][j]=0;
        for (int id=1; id<=n; id++){
            if (pos[id].first<0) continue;
            int r = pos[id].first, c = pos[id].second, L = info[id].len;
            if (info[id].horizontal) {
                for (int k=0;k<L;k++) b[r][c+k]=id;
            } else {
                for (int k=0;k<L;k++) b[r+k][c]=id;
            }
        }
        return b;
    };

    auto is_goal = [&](const vector<pair<int,int>>& pos)->bool{
        // red car id=1, horizontal on row 2 (0-based)
        int r = pos[1].first, c = pos[1].second;
        int L = info[1].len;
        int right_end = c + L - 1;
        return (right_end == 5);
    };

    // BFS for minimal steps
    unordered_map<string,int> dist;
    queue<vector<pair<int,int>>> q;
    vector<pair<int,int>> start = init_pos;

    string key0 = encode(start);
    dist[key0] = 0;
    q.push(start);

    int answer = -1;
    while(!q.empty()){
        auto cur = q.front(); q.pop();
        int d = dist[encode(cur)];
        if (is_goal(cur)) {
            answer = d;
            break;
        }
        auto board = build_board(cur);
        for (int id=1; id<=n; id++){
            int r = cur[id].first, c = cur[id].second, L = info[id].len;
            if (info[id].horizontal) {
                // move left
                int nc = c - 1;
                while (nc >= 0 && board[r][nc] == 0) {
                    auto nxt = cur;
                    nxt[id] = {r, nc};
                    string k = encode(nxt);
                    if (!dist.count(k)) {
                        dist[k] = d + 1;
                        q.push(nxt);
                    }
                    nc--;
                }
                // move right
                nc = c + 1;
                while (c + L <= 5 && board[r][c + L] == 0) {
                    auto nxt = cur;
                    nxt[id] = {r, nc};
                    string k = encode(nxt);
                    if (!dist.count(k)) {
                        dist[k] = d + 1;
                        q.push(nxt);
                    }
                    c++;
                    nc++;
                }
            } else {
                // move up
                int nr = r - 1;
                while (nr >= 0 && board[nr][c] == 0) {
                    auto nxt = cur;
                    nxt[id] = {nr, c};
                    string k = encode(nxt);
                    if (!dist.count(k)) {
                        dist[k] = d + 1;
                        q.push(nxt);
                    }
                    nr--;
                }
                // move down
                nr = r + 1;
                while (r + L <= 5 && board[r + L][c] == 0) {
                    auto nxt = cur;
                    nxt[id] = {nr, c};
                    string k = encode(nxt);
                    if (!dist.count(k)) {
                        dist[k] = d + 1;
                        q.push(nxt);
                    }
                    r++;
                    nr++;
                }
            }
        }
    }

    if (answer < 0) answer = 0; // fallback, though guaranteed solvable

    // We choose not to modify the puzzle (0 moves)
    cout << answer << " " << 0 << "\n";
    return 0;
}