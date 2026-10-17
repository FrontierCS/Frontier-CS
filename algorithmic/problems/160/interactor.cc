#include <cmath>
#include <algorithm>

// Scores are in points here. Preserve the previous lower band, and compare
// the original objective with its 60-point anchor using the natural logarithm.
static double natural_log_score(double old_points, long double value,
                                long double anchor, bool minimize) {
    if (minimize && value == 0.0L) return 100.0;
    if (old_points <= 60.0) return old_points;
    // A zero reference or a flat legacy score has no positive logarithmic anchor.
    if (!(value > 0.0L) || !(anchor > 0.0L)) return old_points;
    const long double gain = minimize ? std::log(anchor) - std::log(value)
                                      : std::log(value) - std::log(anchor);
    return static_cast<double>(std::min(100.0L, 60.0L + gain));
}

#include "testlib.h"
#include <bits/stdc++.h>
using namespace std;

static const int N = 10;
static const int M = 3;

struct Input {
    vector<long long> fs; // flavors
    vector<long long> ps; // positions
};

struct State {
    vector<long long> fs;
    vector<long long> ps;
    vector<vector<long long>> board;
    int t;
    pair<int,int> last;

    State(const Input& in) {
        fs = in.fs;
        ps = in.ps;
        board.assign(N, vector<long long>(N, 0));
        t = 0;
        // place first candy at ps[0]
        int p = 0;
        int li = 0, lj = 0;
        for (int i = 0; i < N; i++) {
            for (int j = 0; j < N; j++) {
                if (board[i][j] == 0) {
                    p += 1;
                    if (p == ps[0]) {
                        board[i][j] = fs[0];
                        li = i; lj = j;
                    }
                }
            }
        }
        last = {li, lj};
    }

    void apply_move(char dir) {
        if (dir == 'L') {
            for (int i = 0; i < N; i++) {
                int k = 0;
                for (int j = 0; j < N; j++) {
                    if (board[i][j] != 0) {
                        board[i][k] = board[i][j];
                        if (k != j) board[i][j] = 0;
                        k++;
                    }
                }
            }
        } else if (dir == 'R') {
            for (int i = 0; i < N; i++) {
                int k = N - 1;
                for (int j = N - 1; j >= 0; j--) {
                    if (board[i][j] != 0) {
                        board[i][k] = board[i][j];
                        if (k != j) board[i][j] = 0;
                        k--;
                    }
                }
            }
        } else if (dir == 'F') {
            for (int j = 0; j < N; j++) {
                int k = 0;
                for (int i = 0; i < N; i++) {
                    if (board[i][j] != 0) {
                        board[k][j] = board[i][j];
                        if (k != i) board[i][j] = 0;
                        k++;
                    }
                }
            }
        } else if (dir == 'B') {
            for (int j = 0; j < N; j++) {
                int k = N - 1;
                for (int i = N - 1; i >= 0; i--) {
                    if (board[i][j] != 0) {
                        board[k][j] = board[i][j];
                        if (k != i) board[i][j] = 0;
                        k--;
                    }
                }
            }
        } else {
            quitf(_wa, "Illegal output: %c", dir);
        }

        // place next candy
        t += 1;
        if (t >= N * N) return;
        int p = 0;
        bool placed = false;
        for (int i = 0; i < N && !placed; i++) {
            for (int j = 0; j < N && !placed; j++) {
                if (board[i][j] == 0) {
                    p += 1;
                    if (p == ps[t]) {
                        board[i][j] = fs[t];
                        last = {i, j};
                        placed = true;
                    }
                }
            }
        }
        if (!placed) {
            quitf(_fail, "Internal error: could not place candy at turn %d", t);
        }
    }
};

static long long physical_cluster_sum = 0, physical_color_sum = 0;
static long long compute_score(const Input& in, const vector<char>& out_moves) {
    State st(in);
    int steps = (int)min<long long>((long long)out_moves.size(), (long long)N * N - 1);
    for (int t = 0; t < steps; t++) {
        char dir = out_moves[t];
        if (!(dir == 'L' || dir == 'R' || dir == 'F' || dir == 'B')) {
            quitf(_wa, "Illegal output: %c (turn: %d)", dir, t);
        }
        st.apply_move(dir);
    }

    // compute connectivity
    vector<vector<int>> vis(N, vector<int>(N, 0));
    long long num = 0;
    const int di[4] = {1, 0, -1, 0};
    const int dj[4] = {0, 1, 0, -1};
    for (int i = 0; i < N; i++) {
        for (int j = 0; j < N; j++) {
            if (!vis[i][j] && st.board[i][j] != 0) {
                vis[i][j] = 1;
                long long c = st.board[i][j];
                long long sz = 1;
                vector<pair<int,int>> stk;
                stk.emplace_back(i, j);
                while (!stk.empty()) {
                    auto [ii, jj] = stk.back(); stk.pop_back();
                    for (int d = 0; d < 4; d++) {
                        int ni = ii + di[d], nj = jj + dj[d];
                        if (0 <= ni && ni < N && 0 <= nj && nj < N && !vis[ni][nj] && st.board[ni][nj] == c) {
                            vis[ni][nj] = 1;
                            stk.emplace_back(ni, nj);
                            sz++;
                        }
                    }
                }
                num += sz * sz;
            }
        }
    }

    vector<long long> d(M + 1, 0);
    for (auto f : in.fs) {
        if (1 <= f && f <= M) d[(int)f] += 1;
        else quitf(_fail, "Internal error: flavor out of range");
    }
    long long denom = 0;
    for (int i = 1; i <= M; i++) denom += d[i] * d[i];
    physical_cluster_sum = num;
    physical_color_sum = denom;
    if (denom == 0) return 0;
    long long score = llround(1e6L * (long double)num / (long double)denom);
    return score;
}

static string strip(const string& s) {
    size_t l = 0, r = s.size();
    while (l < r && isspace((unsigned char)s[l])) l++;
    while (r > l && isspace((unsigned char)s[r - 1])) r--;
    return s.substr(l, r - l);
}

int main(int argc, char* argv[]) {
    registerInteraction(argc, argv);

    Input in;
    in.fs.resize(N * N);
    in.ps.resize(N * N);

    // Read fs
    for (int i = 0; i < N * N; i++) {
        in.fs[i] = inf.readInt();
    }
    // Read ps
    for (int i = 0; i < N * N; i++) {
        in.ps[i] = inf.readInt();
    }

    // Send fs line
    for (int i = 0; i < N * N; i++) {
        if (i) cout << ' ';
        cout << in.fs[i];
    }
    cout << endl;

    vector<char> out_moves;
    out_moves.reserve(N * N - 1);

    for (int t = 0; t < N * N; t++) {
        // Send p_t
        cout << in.ps[t] << endl;

        // No output expected after the 100th tilt (t == N*N - 1)
        if (t == N * N - 1) break;

        // Read contestant move (non-empty line)
        string line;
        do {
            line = ouf.readLine();
            line = strip(line);
        } while (line.empty());

        if ((int)line.size() != 1) {
            quitf(_wa, "Illegal output: %s", line.c_str());
        }
        char dir = line[0];
        if (!(dir == 'L' || dir == 'R' || dir == 'F' || dir == 'B')) {
            quitf(_wa, "Illegal output: %c", dir);
        }
        out_moves.push_back(dir);
    }

    long long score = compute_score(in, out_moves);
    long long baseline_value = ans.readLong();
    long long best_value = ans.readLong();

    // External calibration anchors do not limit the feasible raw objective.
    double gap = (double)best_value - (double)baseline_value;
    // A dominated reference cannot define a decreasing quality scale.
    bool theoretical_anchor = gap <= 0.0;
    if (theoretical_anchor) gap = 1000000.0 - (double)baseline_value;
    ensuref(gap > 0.0, "Invalid calibration anchors");
    double calibration_ratio = max(0.0, ((double)score - (double)baseline_value) / gap);
    double score_ratio = calibration_ratio <= 1.0 ? 0.6 * calibration_ratio : 0.6 + 0.02 * log(calibration_ratio);
    if (theoretical_anchor) score_ratio = min(1.0, calibration_ratio);
    score_ratio = natural_log_score(100.0 * score_ratio, physical_cluster_sum, (long double)physical_color_sum * (theoretical_anchor ? (long double)baseline_value + 0.6L*gap : (long double)best_value) / 1e6L, false) / 100.0;
    quitp(score_ratio, "Value: %lld. Ratio: %.12f, RatioUnbounded: %.12f", score, score_ratio, score_ratio);
    // quitf(_wa, "score (%lld)", score);
    return 0;
}
