#include <bits/stdc++.h>
using namespace std;

int di[4] = {0, -1, 0, 1};
int dj[4] = {-1, 0, 1, 0};
int to_[8][4] = {
    {1, 0, -1, -1},
    {3, -1, -1, 0},
    {-1, -1, 3, 2},
    {-1, 2, 1, -1},
    {1, 0, 3, 2},
    {3, 2, 1, 0},
    {2, -1, 0, -1},
    {-1, 3, -1, 1}
};

int effective(int t, int r) {
    if (t <= 3) return (t + r) % 4;
    if (t <= 5) return 4 + ((t - 4 + r) % 2);
    return 6 + ((t - 6 + r) % 2);
}

long long compute_score(int rot[30][30], int initial[30][30]) {
    int tiles[30][30];
    for (int i = 0; i < 30; i++) {
        for (int j = 0; j < 30; j++) {
            tiles[i][j] = effective(initial[i][j], rot[i][j]);
        }
    }
    const int N = 30 * 30 * 4;
    vector<int> nexts(N, -1);
    auto state = [&](int i, int j, int d) { return (i * 30 + j) * 4 + d; };
    for (int i = 0; i < 30; i++) {
        for (int j = 0; j < 30; j++) {
            int t = tiles[i][j];
            for (int d = 0; d < 4; d++) {
                int d2 = to_[t][d];
                if (d2 == -1) continue;
                int ni = i + di[d2];
                int nj = j + dj[d2];
                if (ni < 0 || ni >= 30 || nj < 0 || nj >= 30) continue;
                int nd = (d2 + 2) % 4;
                int s = state(i, j, d);
                int ns = state(ni, nj, nd);
                nexts[s] = ns;
            }
        }
    }
    vector<bool> visited(N, false);
    vector<int> cycle_lengths;
    vector<char> onpath(N, 0);
    vector<int> path_nodes;
    for (int si = 0; si < N; si++) {
        if (visited[si] || nexts[si] == -1) continue;
        path_nodes.clear();
        int cur = si;
        bool cycle_found = false;
        while (!visited[cur] && nexts[cur] != -1) {
            visited[cur] = true;
            path_nodes.push_back(cur);
            onpath[cur] = 1;
            cur = nexts[cur];
            if (onpath[cur]) {
                int cycle_start = -1;
                for (int k = 0; k < (int)path_nodes.size(); k++) {
                    if (path_nodes[k] == cur) {
                        cycle_start = k;
                        break;
                    }
                }
                if (cycle_start != -1) {
                    int len = path_nodes.size() - cycle_start;
                    cycle_lengths.push_back(len);
                }
                cycle_found = true;
                break;
            }
        }
        for (int p : path_nodes) onpath[p] = 0;
    }
    if (cycle_lengths.empty()) return 0;
    map<int, int> cnt;
    for (int len : cycle_lengths) cnt[len]++;
    vector<int> loops;
    for (auto& p : cnt) {
        int num = p.second / 2;
        for (int k = 0; k < num; k++) {
            loops.push_back(p.first);
        }
    }
    if ((int)loops.size() < 2) return 0;
    sort(loops.rbegin(), loops.rend());
    return (long long)loops[0] * loops[1];
}

int main() {
    srand(time(0));
    int initial[30][30];
    for (int i = 0; i < 30; i++) {
        string s;
        cin >> s;
        for (int j = 0; j < 30; j++) {
            initial[i][j] = s[j] - '0';
        }
    }
    int best_rot[30][30];
    long long best_score = -1;
    for (int start = 0; start < 3; start++) {
        int rot[30][30];
        for (int i = 0; i < 30; i++) {
            for (int j = 0; j < 30; j++) {
                rot[i][j] = rand() % 4;
            }
        }
        long long cur_score = compute_score(rot, initial);
        bool changed = true;
        int passes = 0;
        while (changed && passes < 50) {
            changed = false;
            long long prev_score = cur_score;
            for (int ii = 0; ii < 30; ii++) {
                for (int jj = 0; jj < 30; jj++) {
                    int orig_r = rot[ii][jj];
                    long long bsc = cur_score;
                    int br = orig_r;
                    for (int rr = 0; rr < 4; rr++) {
                        if (rr == orig_r) continue;
                        rot[ii][jj] = rr;
                        long long sc = compute_score(rot, initial);
                        if (sc > bsc) {
                            bsc = sc;
                            br = rr;
                        }
                    }
                    rot[ii][jj] = orig_r;
                    if (bsc > cur_score) {
                        rot[ii][jj] = br;
                        cur_score = bsc;
                        changed = true;
                    }
                }
            }
            passes++;
        }
        if (cur_score > best_score) {
            best_score = cur_score;
            memcpy(best_rot, rot, sizeof(rot));
        }
    }
    string out = "";
    for (int i = 0; i < 30; i++) {
        for (int j = 0; j < 30; j++) {
            out += '0' + best_rot[i][j];
        }
    }
    cout << out << endl;
    return 0;
}