#include <bits/stdc++.h>
using namespace std;

int TO[8][4] = {
    {1, 0, -1, -1},
    {3, -1, -1, 0},
    {-1, -1, 3, 2},
    {-1, 2, 1, -1},
    {1, 0, 3, 2},
    {3, 2, 1, 0},
    {2, -1, 0, -1},
    {-1, 3, -1, 1}
};

int DX[4] = {0, -1, 0, 1};
int DY[4] = {-1, 0, 1, 0};

int eff_type[8][4] = {
    {0,1,2,3},
    {1,2,3,0},
    {2,3,0,1},
    {3,0,1,2},
    {4,5,4,5},
    {5,4,5,4},
    {6,7,6,7},
    {7,6,7,6}
};

int get_code(int i, int j, int d) {
    return (i * 30 + j) * 4 + d;
}

long long compute_score(const int tiles[30][30]) {
    bool visited[30][30][4];
    memset(visited, 0, sizeof(visited));
    vector<int> cycles;
    for (int si = 0; si < 30; si++) {
        for (int sj = 0; sj < 30; sj++) {
            for (int sd = 0; sd < 4; sd++) {
                if (TO[tiles[si][sj]][sd] == -1) continue;
                if (visited[si][sj][sd]) continue;
                unordered_map<long long, int> pos_in_path;
                vector<tuple<int, int, int>> path;
                int i = si, j = sj, d = sd;
                int step = 0;
                while (true) {
                    long long code = get_code(i, j, d);
                    if (pos_in_path.count(code)) {
                        int cstart = pos_in_path[code];
                        int clen = step - cstart;
                        cycles.push_back(clen);
                        break;
                    }
                    if (visited[i][j][d]) {
                        break;
                    }
                    pos_in_path[code] = step;
                    path.emplace_back(i, j, d);
                    step++;
                    int d2 = TO[tiles[i][j]][d];
                    if (d2 == -1) break;
                    int ni = i + DX[d2];
                    int nj = j + DY[d2];
                    if (ni < 0 || ni >= 30 || nj < 0 || nj >= 30) break;
                    d = (d2 + 2) % 4;
                    i = ni;
                    j = nj;
                }
                for (auto& p : path) {
                    int pi, pj, pd;
                    tie(pi, pj, pd) = p;
                    visited[pi][pj][pd] = true;
                }
            }
        }
    }
    if (cycles.size() < 2) return 0;
    sort(cycles.rbegin(), cycles.rend());
    return (long long)cycles[0] * cycles[1];
}

int main() {
    srand(time(NULL));
    int orig[30][30];
    for (int i = 0; i < 30; i++) {
        string s;
        cin >> s;
        for (int j = 0; j < 30; j++) {
            orig[i][j] = s[j] - '0';
        }
    }
    long long best_score = -1;
    string best_rot_str = string(900, '0');
    const int TRIALS = 100000;
    for (int trial = 0; trial < TRIALS; trial++) {
        int r[30][30];
        for (int i = 0; i < 30; i++) {
            for (int j = 0; j < 30; j++) {
                r[i][j] = rand() % 4;
            }
        }
        int tiles[30][30];
        for (int i = 0; i < 30; i++) {
            for (int j = 0; j < 30; j++) {
                tiles[i][j] = eff_type[orig[i][j]][r[i][j]];
            }
        }
        long long score = compute_score(tiles);
        if (score > best_score) {
            best_score = score;
            string cur_str = "";
            for (int i = 0; i < 30; i++) {
                for (int j = 0; j < 30; j++) {
                    cur_str += '0' + r[i][j];
                }
            }
            best_rot_str = cur_str;
        }
    }
    cout << best_rot_str << endl;
    return 0;
}