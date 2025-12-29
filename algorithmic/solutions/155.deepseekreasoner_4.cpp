#include <bits/stdc++.h>
using namespace std;

const int H = 20, W = 20;
const int dirs[4][2] = {{-1,0},{1,0},{0,-1},{0,1}}; // U,D,L,R
const char dir_char[4] = {'U','D','L','R'};
const int opp[4] = {1,0,3,2}; // opposite directions

bool can[4][H][W]; // can[move][i][j]

double dp[H][W];
double ndp[H][W];
double arrival[201]; // probability of arriving exactly at step t

double evaluate(const string& s, int si, int sj, int ti, int tj, double p) {
    int L = s.size();
    for (int i = 0; i < H; i++) for (int j = 0; j < W; j++) dp[i][j] = 0;
    dp[si][sj] = 1.0;
    fill(arrival, arrival+L+1, 0.0);

    for (int t = 1; t <= L; t++) {
        for (int i = 0; i < H; i++) for (int j = 0; j < W; j++) ndp[i][j] = 0;
        char c = s[t-1];
        int d;
        if (c == 'U') d = 0;
        else if (c == 'D') d = 1;
        else if (c == 'L') d = 2;
        else d = 3;

        for (int i = 0; i < H; i++) {
            for (int j = 0; j < W; j++) {
                double prob = dp[i][j];
                if (prob == 0.0) continue;
                // forget
                ndp[i][j] += prob * p;
                // try to move
                if (can[d][i][j]) {
                    int ni = i + dirs[d][0];
                    int nj = j + dirs[d][1];
                    if (ni == ti && nj == tj) {
                        arrival[t] += prob * (1-p);
                    } else {
                        ndp[ni][nj] += prob * (1-p);
                    }
                } else {
                    ndp[i][j] += prob * (1-p);
                }
            }
        }
        // copy back
        for (int i = 0; i < H; i++) for (int j = 0; j < W; j++) dp[i][j] = ndp[i][j];
    }

    double expected = 0.0;
    for (int t = 1; t <= L; t++) {
        expected += (401 - t) * arrival[t];
    }
    return expected;
}

string bfs_shortest_path(int si, int sj, int ti, int tj) {
    int dist[H][W];
    pair<int,int> parent[H][W]; // parent cell
    int pdir[H][W]; // direction from parent to this cell
    for (int i = 0; i < H; i++) for (int j = 0; j < W; j++) dist[i][j] = -1;
    queue<pair<int,int>> q;
    dist[si][sj] = 0;
    q.push({si,sj});
    while (!q.empty()) {
        auto [i,j] = q.front(); q.pop();
        if (i == ti && j == tj) break;
        for (int d = 0; d < 4; d++) {
            if (!can[d][i][j]) continue;
            int ni = i + dirs[d][0];
            int nj = j + dirs[d][1];
            if (dist[ni][nj] == -1) {
                dist[ni][nj] = dist[i][j] + 1;
                parent[ni][nj] = {i,j};
                pdir[ni][nj] = d;
                q.push({ni,nj});
            }
        }
    }
    // reconstruct path from target to start
    string path = "";
    int i = ti, j = tj;
    while (!(i == si && j == sj)) {
        auto [pi,pj] = parent[i][j];
        int d = pdir[i][j]; // direction from parent to current
        path += dir_char[opp[d]]; // we need move from current to parent, which is opposite
        i = pi; j = pj;
    }
    reverse(path.begin(), path.end());
    return path;
}

// Find a short cycle (length <= max_len) starting and ending at (ti,tj)
string find_cycle(int ti, int tj, int max_len) {
    int dist[H][W];
    pair<int,int> parent[H][W];
    int pdir[H][W];
    for (int i = 0; i < H; i++) for (int j = 0; j < W; j++) dist[i][j] = -1;
    queue<pair<int,int>> q;
    dist[ti][tj] = 0;
    q.push({ti,tj});
    while (!q.empty()) {
        auto [i,j] = q.front(); q.pop();
        if (dist[i][j] >= max_len) continue;
        for (int d = 0; d < 4; d++) {
            if (!can[d][i][j]) continue;
            int ni = i + dirs[d][0];
            int nj = j + dirs[d][1];
            if (dist[ni][nj] == -1) {
                dist[ni][nj] = dist[i][j] + 1;
                parent[ni][nj] = {i,j};
                pdir[ni][nj] = d;
                q.push({ni,nj});
            }
        }
    }
    // Find a neighbor with shortest path back to target
    int best_len = 1000;
    int best_dir = -1;
    pair<int,int> best_neigh;
    for (int d = 0; d < 4; d++) {
        if (!can[d][ti][tj]) continue;
        int ni = ti + dirs[d][0];
        int nj = tj + dirs[d][1];
        if (dist[ni][nj] != -1 && dist[ni][nj] + 1 <= max_len) {
            int len = dist[ni][nj] + 1;
            if (len < best_len) {
                best_len = len;
                best_dir = d;
                best_neigh = {ni,nj};
            }
        }
    }
    if (best_dir == -1) return "";
    // reconstruct cycle: first move to neighbor, then path back to target
    string cycle = "";
    cycle += dir_char[best_dir];
    int i = best_neigh.first, j = best_neigh.second;
    while (!(i == ti && j == tj)) {
        auto [pi,pj] = parent[i][j];
        int d = pdir[i][j]; // direction from parent to current
        cycle += dir_char[opp[d]]; // move from current to parent
        i = pi; j = pj;
    }
    return cycle;
}

int main() {
    int si, sj, ti, tj;
    double p;
    cin >> si >> sj >> ti >> tj >> p;

    vector<string> h(H), v(H-1);
    for (int i = 0; i < H; i++) cin >> h[i];
    for (int i = 0; i < H-1; i++) cin >> v[i];

    // Build can[][][]
    for (int i = 0; i < H; i++) {
        for (int j = 0; j < W; j++) {
            // up
            if (i > 0 && v[i-1][j] == '0') can[0][i][j] = true;
            // down
            if (i < H-1 && v[i][j] == '0') can[1][i][j] = true;
            // left
            if (j > 0 && h[i][j-1] == '0') can[2][i][j] = true;
            // right
            if (j < W-1 && h[i][j] == '0') can[3][i][j] = true;
        }
    }

    string shortest = bfs_shortest_path(si, sj, ti, tj);
    int L0 = shortest.size();

    string cycle = find_cycle(ti, tj, 20);
    int Lc = cycle.size();

    vector<string> candidates;

    // Candidate 1: shortest path (truncated to 200)
    if (L0 <= 200) candidates.push_back(shortest);
    else candidates.push_back(shortest.substr(0,200));

    // Candidate 2: shortest path repeated
    {
        string s = "";
        while (s.size() < 200) s += shortest;
        s = s.substr(0,200);
        candidates.push_back(s);
    }

    // Candidate 3: shortest path + cycle repeated (if cycle exists)
    if (Lc > 0) {
        string s = shortest;
        while (s.size() < 200) s += cycle;
        s = s.substr(0,200);
        candidates.push_back(s);
    }

    // Candidate 4,5,6: each move repeated r times (r=2,3,4)
    for (int r = 2; r <= 4; r++) {
        string s = "";
        for (char c : shortest) {
            for (int k = 0; k < r; k++) {
                s += c;
                if (s.size() >= 200) break;
            }
            if (s.size() >= 200) break;
        }
        s = s.substr(0,200);
        candidates.push_back(s);
    }

    // Candidate 7: shortest + reverse shortest
    {
        string rev = shortest;
        reverse(rev.begin(), rev.end());
        string s = shortest + rev;
        if (s.size() > 200) s = s.substr(0,200);
        candidates.push_back(s);
    }

    // Candidate 8: shortest + rev + shortest (if fits)
    {
        string rev = shortest;
        reverse(rev.begin(), rev.end());
        string s = shortest + rev + shortest;
        if (s.size() > 200) s = s.substr(0,200);
        candidates.push_back(s);
    }

    // Evaluate all candidates, choose best expected score
    double best_score = -1;
    string best_str = "";
    for (const string& cand : candidates) {
        double score = evaluate(cand, si, sj, ti, tj, p);
        if (score > best_score) {
            best_score = score;
            best_str = cand;
        }
    }

    cout << best_str << endl;
    return 0;
}