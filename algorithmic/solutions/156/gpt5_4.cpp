#include <bits/stdc++.h>
using namespace std;

struct Timer {
    chrono::steady_clock::time_point st;
    Timer() { reset(); }
    void reset() { st = chrono::steady_clock::now(); }
    double elapsed_ms() const {
        return chrono::duration<double, std::milli>(chrono::steady_clock::now() - st).count();
    }
};

static const int H = 30;
static const int W = 30;
static const int N = H * W;
static const int STATES = N * 4;

int di[4] = {0, -1, 0, 1};  // L,U,R,D
int dj[4] = {-1, 0, 1, 0};

int to_map[8][4] = {
    {1, 0, -1, -1},  // 0
    {3, -1, -1, 0},  // 1
    {-1, -1, 3, 2},  // 2
    {-1, 2, 1, -1},  // 3
    {1, 0, 3, 2},    // 4
    {3, 2, 1, 0},    // 5
    {2, -1, 0, -1},  // 6
    {-1, 3, -1, 1},  // 7
};

int rot_once[8] = {1,2,3,0,5,4,7,6};
int rot_map_tbl[8][4];

inline int idx(int i, int j) { return i * W + j; }
inline bool inb(int i, int j){ return (0 <= i && i < H && 0 <= j && j < W); }

int compute_score(const array<int, N>& finalT, array<int, STATES>& succ) {
    // Build succ
    for (int s = 0; s < STATES; ++s) {
        int v = s / 4;
        int d = s & 3;
        int i = v / W;
        int j = v % W;
        int t = finalT[v];
        int d2 = to_map[t][d];
        if (d2 == -1) {
            succ[s] = -1;
            continue;
        }
        int ni = i + di[d2];
        int nj = j + dj[d2];
        if (!inb(ni, nj)) {
            succ[s] = -1;
            continue;
        }
        int nd = (d2 + 2) & 3;
        succ[s] = ((ni * W + nj) << 2) | nd;
    }

    // Find cycles and compute top two lengths
    static array<int, STATES> root;
    static array<int, STATES> pos;
    root.fill(-1);
    int best1 = 0, best2 = 0;

    for (int s = 0; s < STATES; ++s) {
        int u = s;
        int depth = 0;
        while (u != -1 && root[u] == -1) {
            root[u] = s;
            pos[u] = depth++;
            u = succ[u];
        }
        if (u != -1 && root[u] == s) {
            int len = depth - pos[u];
            if (len >= best1) {
                best2 = best1;
                best1 = len;
            } else if (len > best2) {
                best2 = len;
            }
        }
    }
    if (best2 == 0) return 0;
    return best1 * best2;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    // Precompute rotation table
    for (int t = 0; t < 8; ++t) {
        rot_map_tbl[t][0] = t;
        for (int r = 1; r < 4; ++r) rot_map_tbl[t][r] = rot_once[rot_map_tbl[t][r-1]];
    }

    // Read input
    array<int, N> initialT;
    for (int i = 0; i < H; ++i) {
        string s;
        cin >> s;
        for (int j = 0; j < W; ++j) {
            initialT[idx(i,j)] = s[j] - '0';
        }
    }

    std::mt19937 rng((uint32_t)chrono::steady_clock::now().time_since_epoch().count());

    // Initial rotations (greedy toward matching open sides and avoiding borders if possible)
    array<int, N> rot{};
    rot.fill(0);
    array<int, N> finalT;
    for (int v = 0; v < N; ++v) {
        finalT[v] = rot_map_tbl[initialT[v]][rot[v] & 3];
    }

    auto is_open = [&](int t, int d) -> bool {
        return to_map[t][d] != -1;
    };

    // Greedy local optimization for initial rotations (few passes)
    const int init_passes = 3;
    for (int pass = 0; pass < init_passes; ++pass) {
        for (int i = 0; i < H; ++i) {
            for (int j = 0; j < W; ++j) {
                int v = idx(i, j);
                int best_r = rot[v];
                int best_sc = -1e9;
                for (int rr = 0; rr < 4; ++rr) {
                    int t = rot_map_tbl[initialT[v]][rr];
                    int sc = 0;
                    // Left
                    if (j - 1 >= 0) {
                        int u = idx(i, j - 1);
                        int t2 = finalT[u];
                        sc += (is_open(t, 0) && is_open(t2, 2));
                    } else {
                        if (is_open(t, 0)) sc -= 1; // penalize open to border
                    }
                    // Up
                    if (i - 1 >= 0) {
                        int u = idx(i - 1, j);
                        int t2 = finalT[u];
                        sc += (is_open(t, 1) && is_open(t2, 3));
                    } else {
                        if (is_open(t, 1)) sc -= 1;
                    }
                    // Right
                    if (j + 1 < W) {
                        int u = idx(i, j + 1);
                        int t2 = finalT[u];
                        sc += (is_open(t, 2) && is_open(t2, 0));
                    } else {
                        if (is_open(t, 2)) sc -= 1;
                    }
                    // Down
                    if (i + 1 < H) {
                        int u = idx(i + 1, j);
                        int t2 = finalT[u];
                        sc += (is_open(t, 3) && is_open(t2, 1));
                    } else {
                        if (is_open(t, 3)) sc -= 1;
                    }
                    if (sc > best_sc) {
                        best_sc = sc;
                        best_r = rr;
                    }
                }
                rot[v] = best_r & 3;
                finalT[v] = rot_map_tbl[initialT[v]][rot[v]];
            }
        }
    }

    // Prepare for SA
    array<int, STATES> succ;
    int cur_score = compute_score(finalT, succ);

    array<int, N> best_rot = rot;
    int best_score = cur_score;

    Timer timer;
    const double TIME_LIMIT_MS = 1900.0; // around 1.9s
    const double T0 = 5.0;
    const double T1 = 0.01;

    uniform_int_distribution<int> dist_pos(0, N - 1);
    uniform_int_distribution<int> dist_step(1, 3);
    uniform_real_distribution<double> dist01(0.0, 1.0);

    // Simulated Annealing loop
    int iter = 0;
    while (true) {
        double elapsed = timer.elapsed_ms();
        if (elapsed > TIME_LIMIT_MS) break;
        double progress = elapsed / TIME_LIMIT_MS;
        double T = T0 + (T1 - T0) * progress;

        int v = dist_pos(rng);
        int oldr = rot[v];
        int delta = dist_step(rng);
        int newr = (oldr + delta) & 3;

        int oldT = finalT[v];
        int newT = rot_map_tbl[initialT[v]][newr];

        // Apply tentative change
        rot[v] = newr;
        finalT[v] = newT;

        int new_score = compute_score(finalT, succ);
        int diff = new_score - cur_score;
        bool accept = false;
        if (diff >= 0) {
            accept = true;
        } else {
            double prob = exp((double)diff / T);
            if (dist01(rng) < prob) accept = true;
        }

        if (accept) {
            cur_score = new_score;
            if (cur_score > best_score) {
                best_score = cur_score;
                best_rot = rot;
            }
        } else {
            // revert
            rot[v] = oldr;
            finalT[v] = oldT;
        }

        ++iter;
    }

    // Output best rotations
    string out;
    out.reserve(N);
    for (int i = 0; i < N; ++i) out.push_back(char('0' + (best_rot[i] & 3)));
    cout << out << "\n";
    return 0;
}