#include <bits/stdc++.h>
using namespace std;

const int N = 20;
const int INF = 1e9;

// ------------------------------------------------------------
// walls
vector<vector<bool>> h_wall(N, vector<bool>(N-1, false));
vector<vector<bool>> v_wall(N-1, vector<bool>(N, false));

// ------------------------------------------------------------
// utilities
string repeat_each(const string& s, int k) {
    string res;
    for (char c : s)
        for (int i=0; i<k; ++i)
            res.push_back(c);
    return res;
}

string repeat_whole(const string& s, int r) {
    string res;
    for (int i=0; i<r; ++i) res += s;
    return res;
}

// ------------------------------------------------------------
// check if a cycle returns to (ti,tj) when executed without forgetting
bool is_cycle_valid(const string& cyc, int ti, int tj) {
    int i = ti, j = tj;
    for (char c : cyc) {
        if (c == 'U') {
            if (i == 0 || v_wall[i-1][j]) return false;
            --i;
        } else if (c == 'D') {
            if (i == N-1 || v_wall[i][j]) return false;
            ++i;
        } else if (c == 'L') {
            if (j == 0 || h_wall[i][j-1]) return false;
            --j;
        } else if (c == 'R') {
            if (j == N-1 || h_wall[i][j]) return false;
            ++j;
        }
    }
    return (i == ti && j == tj);
}

// ------------------------------------------------------------
// compute expected score for a given path
double compute_score(const string& path,
                     int si, int sj, int ti, int tj, double p) {
    int L = path.size();
    vector<double> arrival(L+1, 0.0);
    vector<vector<double>> prob(N, vector<double>(N, 0.0));
    prob[si][sj] = 1.0;

    for (int t=0; t<L; ++t) {
        vector<vector<double>> nxt(N, vector<double>(N, 0.0));
        char c = path[t];
        for (int i=0; i<N; ++i) {
            for (int j=0; j<N; ++j) {
                double cur = prob[i][j];
                if (cur == 0.0) continue;
                if (i == ti && j == tj) continue;   // already absorbed

                bool wall = false;
                int ni = i, nj = j;
                if (c == 'U') {
                    if (i == 0 || v_wall[i-1][j]) wall = true;
                    else ni = i-1;
                } else if (c == 'D') {
                    if (i == N-1 || v_wall[i][j]) wall = true;
                    else ni = i+1;
                } else if (c == 'L') {
                    if (j == 0 || h_wall[i][j-1]) wall = true;
                    else nj = j-1;
                } else if (c == 'R') {
                    if (j == N-1 || h_wall[i][j]) wall = true;
                    else nj = j+1;
                }

                double stay_prob, move_prob;
                if (wall) {
                    stay_prob = 1.0;
                    move_prob = 0.0;
                } else {
                    stay_prob = p;
                    move_prob = 1.0 - p;
                }

                // stay part
                nxt[i][j] += cur * stay_prob;
                // move part
                if (move_prob > 0) {
                    if (ni == ti && nj == tj) {
                        arrival[t+1] += cur * move_prob;
                    } else {
                        nxt[ni][nj] += cur * move_prob;
                    }
                }
            }
        }
        prob.swap(nxt);
    }

    double score = 0.0;
    for (int t=1; t<=L; ++t)
        if (arrival[t] > 0)
            score += (401.0 - t) * arrival[t];
    return score;
}

// ------------------------------------------------------------
int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int si, sj, ti, tj;
    double p;
    cin >> si >> sj >> ti >> tj >> p;

    // read horizontal walls
    for (int i=0; i<N; ++i) {
        string line;
        cin >> line;
        for (int j=0; j<N-1; ++j)
            h_wall[i][j] = (line[j] == '1');
    }
    // read vertical walls
    for (int i=0; i<N-1; ++i) {
        string line;
        cin >> line;
        for (int j=0; j<N; ++j)
            v_wall[i][j] = (line[j] == '1');
    }

    // --------------------------------------------------------
    // BFS for a shortest path
    vector<vector<int>> dist(N, vector<int>(N, INF));
    vector<vector<pair<int,int>>> parent(N, vector<pair<int,int>>(N, {-1,-1}));
    vector<vector<char>> dir_char(N, vector<char>(N, '?'));
    const int dx[4] = {-1, 1, 0, 0};
    const int dy[4] = {0, 0, -1, 1};
    const char dc[4] = {'U', 'D', 'L', 'R'};

    queue<pair<int,int>> q;
    dist[si][sj] = 0;
    q.push({si, sj});
    while (!q.empty()) {
        auto [i,j] = q.front(); q.pop();
        if (i == ti && j == tj) break;
        for (int d=0; d<4; ++d) {
            int ni = i + dx[d];
            int nj = j + dy[d];
            if (ni<0 || ni>=N || nj<0 || nj>=N) continue;
            // check wall
            bool wall = false;
            if (d == 0) { // U
                if (i==0 || v_wall[i-1][j]) wall = true;
            } else if (d == 1) { // D
                if (i==N-1 || v_wall[i][j]) wall = true;
            } else if (d == 2) { // L
                if (j==0 || h_wall[i][j-1]) wall = true;
            } else { // R
                if (j==N-1 || h_wall[i][j]) wall = true;
            }
            if (wall) continue;
            if (dist[ni][nj] > dist[i][j] + 1) {
                dist[ni][nj] = dist[i][j] + 1;
                parent[ni][nj] = {i,j};
                dir_char[ni][nj] = dc[d];
                q.push({ni,nj});
            }
        }
    }

    // reconstruct shortest path
    string sp = "";
    int i = ti, j = tj;
    while (!(i==si && j==sj)) {
        sp += dir_char[i][j];
        auto [pi,pj] = parent[i][j];
        i = pi; j = pj;
    }
    reverse(sp.begin(), sp.end());
    int d = sp.size();

    // --------------------------------------------------------
    // generate candidate strings
    vector<string> candidates;
    candidates.push_back(sp);                     // original shortest path

    int max_rep = 200 / d;   // floor
    // 1. repeat each move k times
    for (int k=2; k<=max_rep && k<=10; ++k)
        candidates.push_back(repeat_each(sp, k));
    // 2. repeat whole path r times
    for (int r=2; r<=max_rep && r<=10; ++r)
        candidates.push_back(repeat_whole(sp, r));

    // 3. cycles appended after SP
    vector<string> cycle_patterns = {
        "LDRU", "RDLU", "ULDR", "URDL", "DLUR", "DRUL",
        "LR", "RL", "UD", "DU"
    };
    for (const string& cyc : cycle_patterns) {
        if (is_cycle_valid(cyc, ti, tj)) {
            int clen = cyc.size();
            int max_m = (200 - d) / clen;
            for (int m=1; m<=max_m && m<=5; ++m)
                candidates.push_back(sp + repeat_whole(cyc, m));
        }
    }

    // --------------------------------------------------------
    // evaluate all candidates, keep the best
    double best_score = -1.0;
    string best_string = "";
    for (const string& cand : candidates) {
        if (cand.size() > 200) continue;
        double score = compute_score(cand, si, sj, ti, tj, p);
        if (score > best_score) {
            best_score = score;
            best_string = cand;
        }
    }

    // output
    cout << best_string << endl;
    return 0;
}