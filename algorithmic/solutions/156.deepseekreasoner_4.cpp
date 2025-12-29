#include <bits/stdc++.h>
using namespace std;

const int H = 30, W = 30;
int base[H][W];
int rot[H][W];
int eff_to[H][W][4];
bool visited[H][W][4];

int di[4] = {0, -1, 0, 1};
int dj[4] = {-1, 0, 1, 0};

int base_to[8][4] = {
    {1,0,-1,-1},
    {3,-1,-1,0},
    {-1,-1,3,2},
    {-1,2,1,-1},
    {1,0,3,2},
    {3,2,1,0},
    {2,-1,0,-1},
    {-1,3,-1,1}
};

int rotated_to[8][4][4];

void precompute_rotated() {
    for (int t = 0; t < 8; ++t) {
        for (int r = 0; r < 4; ++r) {
            for (int d = 0; d < 4; ++d) {
                int d_orig = (d + r) % 4;
                int o = base_to[t][d_orig];
                if (o == -1) rotated_to[t][r][d] = -1;
                else rotated_to[t][r][d] = (o - r + 4) % 4;
            }
        }
    }
}

void update_eff_to(int i, int j) {
    int t = base[i][j];
    int r = rot[i][j];
    for (int d = 0; d < 4; ++d)
        eff_to[i][j][d] = rotated_to[t][r][d];
}

vector<int> compute_cycles() {
    for (int i = 0; i < H; ++i)
        for (int j = 0; j < W; ++j)
            for (int d = 0; d < 4; ++d)
                visited[i][j][d] = false;

    vector<int> cycles;
    for (int i = 0; i < H; ++i) {
        for (int j = 0; j < W; ++j) {
            for (int d = 0; d < 4; ++d) {
                if (visited[i][j][d]) continue;
                if (eff_to[i][j][d] == -1) {
                    visited[i][j][d] = true;
                    continue;
                }
                int si = i, sj = j, sd = d;
                int ci = i, cj = j, cd = d;
                int len = 0;
                bool is_cycle = false;
                while (true) {
                    if (len > 0 && ci == si && cj == sj && cd == sd) {
                        is_cycle = true;
                        break;
                    }
                    if (visited[ci][cj][cd]) break;
                    visited[ci][cj][cd] = true;
                    int d2 = eff_to[ci][cj][cd];
                    if (d2 == -1) break;
                    int ni = ci + di[d2];
                    int nj = cj + dj[d2];
                    if (ni < 0 || ni >= H || nj < 0 || nj >= W) break;
                    int nd = (d2 + 2) % 4;
                    ci = ni; cj = nj; cd = nd;
                    ++len;
                }
                if (is_cycle) cycles.push_back(len);
            }
        }
    }
    return cycles;
}

long long compute_score() {
    vector<int> cycles = compute_cycles();
    if (cycles.size() < 2) return 0;
    sort(cycles.rbegin(), cycles.rend());
    return (long long)cycles[0] * cycles[1];
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    for (int i = 0; i < H; ++i) {
        string s;
        cin >> s;
        for (int j = 0; j < W; ++j)
            base[i][j] = s[j] - '0';
    }

    precompute_rotated();

    for (int i = 0; i < H; ++i)
        for (int j = 0; j < W; ++j)
            rot[i][j] = 0;
    for (int i = 0; i < H; ++i)
        for (int j = 0; j < W; ++j)
            update_eff_to(i, j);

    random_device rd;
    mt19937 gen(rd());
    uniform_int_distribution<> tile_dist(0, H * W - 1);
    uniform_int_distribution<> rot_dist(0, 3);
    uniform_real_distribution<> prob(0.0, 1.0);

    long long current_score = compute_score();
    const int max_iter = 2000;
    double start_temp = 5.0;
    double end_temp = 0.01;

    for (int iter = 0; iter < max_iter; ++iter) {
        int idx = tile_dist(gen);
        int i = idx / W, j = idx % W;
        int old_rot = rot[i][j];
        int new_rot = rot_dist(gen);
        if (new_rot == old_rot) continue;

        rot[i][j] = new_rot;
        update_eff_to(i, j);
        long long new_score = compute_score();

        double temp = start_temp * pow(end_temp / start_temp, (double)iter / max_iter);
        if (new_score > current_score || prob(gen) < exp((new_score - current_score) / temp))
            current_score = new_score;
        else {
            rot[i][j] = old_rot;
            update_eff_to(i, j);
        }
    }

    string ans;
    for (int i = 0; i < H; ++i)
        for (int j = 0; j < W; ++j)
            ans += char('0' + rot[i][j]);
    cout << ans << endl;

    return 0;
}