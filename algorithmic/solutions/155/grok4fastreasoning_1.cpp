#include <bits/stdc++.h>
using namespace std;

int main() {
    int si, sj, ti, tj;
    double p;
    cin >> si >> sj >> ti >> tj >> p;
    vector<string> h(20);
    for (int i = 0; i < 20; i++) cin >> h[i];
    vector<string> v(19);
    for (int i = 0; i < 19; i++) cin >> v[i];

    int di[4] = {-1, 1, 0, 0};
    int dj[4] = {0, 0, -1, 1};

    auto can_move = [&](int ci, int cj, int cd, const vector<string>& hh, const vector<string>& vv) -> bool {
        int ni = ci + di[cd];
        int nj = cj + dj[cd];
        if (ni < 0 || ni > 19 || nj < 0 || nj > 19) return false;
        if (cd == 0) {
            return vv[ni][nj] == '0';
        } else if (cd == 1) {
            return vv[ci][cj] == '0';
        } else if (cd == 2) {
            return hh[ci][nj] == '0';
        } else {
            return hh[ci][cj] == '0';
        }
    };

    auto compute_E = [&](const string& seq, int start_i, int start_j, int goal_i, int goal_j, double pp,
                         const vector<string>& hh, const vector<string>& vv) -> double {
        int L = seq.size();
        vector<vector<double>> prob(20, vector<double>(20, 0.0));
        prob[start_i][start_j] = 1.0;
        double expect = 0.0;
        vector<vector<bool>> isgoal(20, vector<bool>(20, false));
        isgoal[goal_i][goal_j] = true;
        auto to_d = [](char c) -> int {
            if (c == 'U') return 0;
            if (c == 'D') return 1;
            if (c == 'L') return 2;
            return 3;
        };
        for (int t = 0; t < L; t++) {
            vector<vector<double>> nprob(20, vector<double>(20, 0.0));
            char ch = seq[t];
            int cd = to_d(ch);
            for (int i = 0; i < 20; i++) {
                for (int j = 0; j < 20; j++) {
                    double pr = prob[i][j];
                    if (pr == 0.0) continue;
                    nprob[i][j] += pp * pr;
                    double pm = (1.0 - pp) * pr;
                    int ni = i + di[cd];
                    int nj = j + dj[cd];
                    bool movable = can_move(i, j, cd, hh, vv);
                    if (movable) {
                        if (isgoal[ni][nj]) {
                            expect += pm * (401 - (t + 1));
                        } else {
                            nprob[ni][nj] += pm;
                        }
                    } else {
                        nprob[i][j] += pm;
                    }
                }
            }
            prob = move(nprob);
        }
        return expect;
    };

    vector<vector<int>> dist(20, vector<int>(20, -1));
    vector<vector<pair<int, int>>> prev(20, vector<pair<int, int>>(20, {-1, -1}));
    queue<pair<int, int>> q;
    q.push({si, sj});
    dist[si][sj] = 0;
    while (!q.empty()) {
        auto [i, j] = q.front();
        q.pop();
        for (int d = 0; d < 4; d++) {
            int ni = i + di[d];
            int nj = j + dj[d];
            if (ni >= 0 && ni < 20 && nj >= 0 && nj < 20 && can_move(i, j, d, h, v) && dist[ni][nj] == -1) {
                dist[ni][nj] = dist[i][j] + 1;
                prev[ni][nj] = {i, j};
                q.push({ni, nj});
            }
        }
    }

    vector<pair<int, int>> path_pos;
    pair<int, int> cur = {ti, tj};
    while (cur != make_pair(-1, -1)) {
        path_pos.push_back(cur);
        cur = prev[cur.first][cur.second];
    }
    reverse(path_pos.begin(), path_pos.end());

    string path_str = "";
    for (size_t k = 0; k + 1 < path_pos.size(); k++) {
        int i1 = path_pos[k].first, j1 = path_pos[k].second;
        int i2 = path_pos[k + 1].first, j2 = path_pos[k + 1].second;
        int ddi = i2 - i1;
        int ddj = j2 - j1;
        if (ddi == -1 && ddj == 0) path_str += 'U';
        else if (ddi == 1 && ddj == 0) path_str += 'D';
        else if (ddi == 0 && ddj == -1) path_str += 'L';
        else if (ddi == 0 && ddj == 1) path_str += 'R';
    }

    int D = path_str.size();
    double best_e = -1.0;
    string best_str = "";
    int maxk = 200 / D;
    if (D == 0) maxk = 1;
    for (int k = 1; k <= maxk; k++) {
        string cand = "";
        for (int rep = 0; rep < k; rep++) {
            cand += path_str;
        }
        double e = compute_E(cand, si, sj, ti, tj, p, h, v);
        if (e > best_e) {
            best_e = e;
            best_str = cand;
        }
    }
    if (best_str.empty()) best_str = path_str;
    cout << best_str << endl;
}