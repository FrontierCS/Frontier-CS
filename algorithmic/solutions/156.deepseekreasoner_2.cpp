#include <bits/stdc++.h>
using namespace std;

const int N = 30;
const int ITER = 2000;
const double T0 = 10000.0;
const double T1 = 1.0;

int base[N][N];
int rot[N][N];
int state[N][N];
int best_rot[N][N];
long long best_score = -1;

int di[4] = {0, -1, 0, 1};
int dj[4] = {-1, 0, 1, 0};

int to[8][4] = {
    {1,0,-1,-1},
    {3,-1,-1,0},
    {-1,-1,3,2},
    {-1,2,1,-1},
    {1,0,3,2},
    {3,2,1,0},
    {2,-1,0,-1},
    {-1,3,-1,1}
};

int next_state[8] = {1,2,3,0,5,4,7,6};
int rotated_state[8][4];

void precompute() {
    for (int t = 0; t < 8; ++t) {
        rotated_state[t][0] = t;
        for (int r = 1; r < 4; ++r) {
            rotated_state[t][r] = next_state[rotated_state[t][r-1]];
        }
    }
}

long long compute_score() {
    static bool vis[N][N][4];
    memset(vis, 0, sizeof(vis));
    long long max1 = 0, max2 = 0;
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            for (int d = 0; d < 4; ++d) {
                if (vis[i][j][d]) continue;
                if (to[state[i][j]][d] == -1) {
                    vis[i][j][d] = true;
                    continue;
                }
                int si = i, sj = j, sd = d;
                int ci = i, cj = j, cd = d;
                long long len = 0;
                while (true) {
                    if (vis[ci][cj][cd]) {
                        if (ci == si && cj == sj && cd == sd) {
                            if (len > max1) {
                                max2 = max1;
                                max1 = len;
                            } else if (len > max2) {
                                max2 = len;
                            }
                        }
                        break;
                    }
                    vis[ci][cj][cd] = true;
                    int d2 = to[state[ci][cj]][cd];
                    if (d2 == -1) break;
                    int ni = ci + di[d2];
                    int nj = cj + dj[d2];
                    if (ni < 0 || ni >= N || nj < 0 || nj >= N) break;
                    int nd = (d2 + 2) % 4;
                    ci = ni;
                    cj = nj;
                    cd = nd;
                    ++len;
                    if (ci == si && cj == sj && cd == sd) {
                        if (len > max1) {
                            max2 = max1;
                            max1 = len;
                        } else if (len > max2) {
                            max2 = len;
                        }
                        break;
                    }
                }
            }
        }
    }
    return max1 * max2;
}

int main() {
    precompute();

    // Read input
    for (int i = 0; i < N; ++i) {
        string line;
        cin >> line;
        for (int j = 0; j < N; ++j) {
            base[i][j] = line[j] - '0';
        }
    }

    // Random initialization
    mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());
    uniform_int_distribution<int> rot_dist(0, 3);
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            rot[i][j] = rot_dist(rng);
            state[i][j] = rotated_state[base[i][j]][rot[i][j]];
        }
    }

    best_score = compute_score();
    memcpy(best_rot, rot, sizeof(rot));
    long long current_score = best_score;

    // Simulated annealing
    uniform_int_distribution<int> tile_dist(0, N - 1);
    uniform_real_distribution<double> prob(0.0, 1.0);

    for (int iter = 0; iter < ITER; ++iter) {
        int i = tile_dist(rng);
        int j = tile_dist(rng);
        int old_rot = rot[i][j];
        int new_rot;
        do {
            new_rot = rot_dist(rng);
        } while (new_rot == old_rot);

        int old_state = state[i][j];
        int new_state = rotated_state[base[i][j]][new_rot];
        state[i][j] = new_state;

        long long new_score = compute_score();

        double T = T0 * pow(T1 / T0, (double)iter / ITER);
        if (new_score > current_score || prob(rng) < exp((new_score - current_score) / T)) {
            current_score = new_score;
            rot[i][j] = new_rot;
            if (new_score > best_score) {
                best_score = new_score;
                memcpy(best_rot, rot, sizeof(rot));
            }
        } else {
            state[i][j] = old_state;
        }
    }

    // Output
    string ans(900, '0');
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            ans[i * N + j] = '0' + best_rot[i][j];
        }
    }
    cout << ans << endl;

    return 0;
}