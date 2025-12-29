#include <bits/stdc++.h>
using namespace std;

const int di[4] = {0, -1, 0, 1};
const int dj[4] = {-1, 0, 1, 0};

int to_base[8][4] = {
    {1, 0, -1, -1},
    {3, -1, -1, 0},
    {-1, -1, 3, 2},
    {-1, 2, 1, -1},
    {1, 0, 3, 2},
    {3, 2, 1, 0},
    {2, -1, 0, -1},
    {-1, 3, -1, 1}
};

int to_rot[8][4][4];
int active_mask[8][4];

void precompute() {
    for (int t = 0; t < 8; ++t) {
        for (int r = 0; r < 4; ++r) {
            for (int d = 0; d < 4; ++d) {
                int rel_in = (d - r + 4) % 4;
                int rel_out = to_base[t][rel_in];
                to_rot[t][r][d] = (rel_out == -1) ? -1 : (rel_out + r) % 4;
            }
            int mask = 0;
            if (t == 0) mask |= (1 << ((0+r)%4)) | (1 << ((1+r)%4));
            else if (t == 1) mask |= (1 << ((0+r)%4)) | (1 << ((3+r)%4));
            else if (t == 2) mask |= (1 << ((2+r)%4)) | (1 << ((3+r)%4));
            else if (t == 3) mask |= (1 << ((1+r)%4)) | (1 << ((2+r)%4));
            else if (t == 4) mask |= (1 << ((0+r)%4)) | (1 << ((1+r)%4)) | (1 << ((2+r)%4)) | (1 << ((3+r)%4));
            else if (t == 5) mask |= (1 << ((0+r)%4)) | (1 << ((1+r)%4)) | (1 << ((2+r)%4)) | (1 << ((3+r)%4));
            else if (t == 6) mask |= (1 << ((0+r)%4)) | (1 << ((2+r)%4));
            else if (t == 7) mask |= (1 << ((1+r)%4)) | (1 << ((3+r)%4));
            active_mask[t][r] = mask;
        }
    }
}

long long compute_score(const vector<vector<int>>& tile, const vector<vector<int>>& rot) {
    static bool visited[30][30][4];
    memset(visited, 0, sizeof(visited));
    vector<int> cycles;
    for (int i = 0; i < 30; ++i) {
        for (int j = 0; j < 30; ++j) {
            for (int d = 0; d < 4; ++d) {
                if (visited[i][j][d]) continue;
                int t = tile[i][j];
                int r = rot[i][j];
                if (to_rot[t][r][d] == -1) {
                    visited[i][j][d] = true;
                    continue;
                }
                int ci = i, cj = j, cd = d;
                int len = 0;
                bool is_cycle = false;
                while (!visited[ci][cj][cd]) {
                    visited[ci][cj][cd] = true;
                    t = tile[ci][cj];
                    r = rot[ci][cj];
                    int d2 = to_rot[t][r][cd];
                    if (d2 == -1) break;
                    int ni = ci + di[d2];
                    int nj = cj + dj[d2];
                    if (ni < 0 || ni >= 30 || nj < 0 || nj >= 30) break;
                    int nd = (d2 + 2) % 4;
                    ci = ni; cj = nj; cd = nd;
                    ++len;
                    if (ci == i && cj == j && cd == d) {
                        is_cycle = true;
                        break;
                    }
                }
                if (is_cycle) cycles.push_back(len);
            }
        }
    }
    if (cycles.empty()) return 0;
    sort(cycles.rbegin(), cycles.rend());
    long long L1 = cycles[0];
    long long L2 = (cycles.size() >= 2 && cycles[1] == cycles[0]) ? cycles[0] : (cycles.size() >= 2 ? cycles[1] : 0);
    return L1 * L2;
}

int main() {
    vector<vector<int>> tile(30, vector<int>(30));
    for (int i = 0; i < 30; ++i) {
        string line;
        cin >> line;
        for (int j = 0; j < 30; ++j) {
            tile[i][j] = line[j] - '0';
        }
    }
    precompute();

    vector<vector<int>> rot(30, vector<int>(30));
    vector<vector<int>> act(30, vector<int>(30));
    mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());

    for (int i = 0; i < 30; ++i) {
        for (int j = 0; j < 30; ++j) {
            rot[i][j] = rng() % 4;
            act[i][j] = active_mask[tile[i][j]][rot[i][j]];
        }
    }

    for (int iter = 0; iter < 10; ++iter) {
        vector<int> order(900);
        iota(order.begin(), order.end(), 0);
        shuffle(order.begin(), order.end(), rng);
        for (int idx : order) {
            int i = idx / 30, j = idx % 30;
            int t = tile[i][j];
            int cur_r = rot[i][j];
            int best_r = cur_r, best_score = -1;
            int neigh_masks[4] = {0};
            for (int d = 0; d < 4; ++d) {
                int ni = i + di[d], nj = j + dj[d];
                if (ni >= 0 && ni < 30 && nj >= 0 && nj < 30)
                    neigh_masks[d] = act[ni][nj];
            }
            for (int r = 0; r < 4; ++r) {
                int mask = active_mask[t][r];
                int score = 0;
                for (int d = 0; d < 4; ++d) {
                    if ((mask >> d) & 1) {
                        int nd = (d + 2) % 4;
                        if ((neigh_masks[d] >> nd) & 1) ++score;
                    }
                }
                if (score > best_score) {
                    best_score = score;
                    best_r = r;
                }
            }
            if (best_r != cur_r) {
                rot[i][j] = best_r;
                act[i][j] = active_mask[t][best_r];
            }
        }
    }

    long long current_score = compute_score(tile, rot);
    long long best_score = current_score;
    auto best_rot = rot;

    const int max_iter = 50000;
    const double T0 = 5000.0;
    uniform_int_distribution<int> tile_dist(0, 29);
    uniform_int_distribution<int> rot_dist(0, 2);
    uniform_real_distribution<double> prob(0, 1);

    for (int iter = 0; iter < max_iter; ++iter) {
        double T = T0 * (1.0 - (double)iter / max_iter);
        int i = tile_dist(rng), j = tile_dist(rng);
        int old_r = rot[i][j];
        int new_r = (old_r + 1 + (rng() % 3)) % 4;
        rot[i][j] = new_r;
        long long new_score = compute_score(tile, rot);
        if (new_score > current_score || prob(rng) < exp((new_score - current_score) / T)) {
            current_score = new_score;
            if (new_score > best_score) {
                best_score = new_score;
                best_rot = rot;
            }
        } else {
            rot[i][j] = old_r;
        }
    }

    string ans(900, '0');
    for (int i = 0; i < 30; ++i)
        for (int j = 0; j < 30; ++j)
            ans[i*30 + j] = '0' + best_rot[i][j];
    cout << ans << endl;
    return 0;
}