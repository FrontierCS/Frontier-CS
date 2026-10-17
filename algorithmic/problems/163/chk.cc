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

static string trimStr(const string& s) {
    size_t l = 0, r = s.size();
    while (l < r && isspace((unsigned char)s[l])) ++l;
    while (r > l && isspace((unsigned char)s[r - 1])) --r;
    return s.substr(l, r - l);
}

static vector<string> splitWS(const string& s) {
    vector<string> tokens;
    string cur;
    for (char ch : s) {
        if (isspace((unsigned char)ch)) {
            if (!cur.empty()) {
                tokens.push_back(cur);
                cur.clear();
            }
        } else {
            cur.push_back(ch);
        }
    }
    if (!cur.empty()) tokens.push_back(cur);
    return tokens;
}

static bool parseLLStrict(const string& t, long long& v) {
    if (t.empty()) return false;
    int i = 0, n = (int)t.size();
    bool neg = false;
    if (t[i] == '+' || t[i] == '-') {
        neg = (t[i] == '-');
        ++i;
    }
    if (i >= n) return false;
    long long x = 0;
    for (; i < n; ++i) {
        if (!isdigit((unsigned char)t[i])) return false;
        int d = t[i] - '0';
        x = x * 10 + d;
    }
    v = neg ? -x : x;
    return true;
}

static vector<vector<char>> get_adj(const vector<vector<long long>>& cs, int m) {
    int n = (int)cs.size();
    vector<vector<char>> adj(m + 1, vector<char>(m + 1, 0));
    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < n; ++j) {
            if (cs[i][j] != 0 && (i == 0 || j == 0 || i + 1 == n || j + 1 == n)) {
                adj[(int)cs[i][j]][0] = 1;
                adj[0][(int)cs[i][j]] = 1;
            }
            if (i + 1 < n && cs[i][j] != cs[i + 1][j]) {
                adj[(int)cs[i][j]][(int)cs[i + 1][j]] = 1;
                adj[(int)cs[i + 1][j]][(int)cs[i][j]] = 1;
            }
            if (j + 1 < n && cs[i][j] != cs[i][j + 1]) {
                adj[(int)cs[i][j]][(int)cs[i][j + 1]] = 1;
                adj[(int)cs[i][j + 1]][(int)cs[i][j]] = 1;
            }
        }
    }
    return adj;
}

int main(int argc, char* argv[]) {
    registerTestlibCmd(argc, argv);

    // Parse input
    long long n = inf.readInt(); // no bounds given here explicitly
    long long m = inf.readInt();
    if (n <= 0 || m <= 0) {
        quitf(_fail, "invalid input: n or m is non-positive");
    }
    vector<vector<long long>> in_cs(n, vector<long long>(n, 0));
    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < n; ++j) {
            in_cs[i][j] = inf.readInt(1, (int)m);
        }
    }

    // Parse output (may contain multiple solutions, use the last complete one)
    vector<vector<vector<long long>>> outs;
    vector<vector<long long>> cur;
    while (!ouf.seekEof()) {
        string line = ouf.readLine();
        string t = trimStr(line);
        if (t.empty()) continue;
        vector<string> toks = splitWS(t);
        if ((int)toks.size() != n) {
            quitf(_wa, "illegal output format");
        }
        vector<long long> row;
        row.reserve(n);
        for (int k = 0; k < n; ++k) {
            long long v;
            if (!parseLLStrict(toks[k], v)) {
                quitf(_wa, "Parse error: %s", toks[k].c_str());
            }
            if (v < 0 || v > m) {
                quitf(_wa, "Out of range: %s", toks[k].c_str());
            }
            row.push_back(v);
        }
        cur.push_back(row);
        if ((int)cur.size() == n) {
            outs.push_back(cur);
            cur.clear();
        }
    }
    if (!cur.empty()) {
        quitf(_wa, "illegal output format");
    }
    if (outs.empty()) {
        quitf(_wa, "empty output");
    }
    const auto& out = outs.back();

    // Compute adjacency matrices and compare
    auto adj0 = get_adj(in_cs, (int)m);
    auto adj1 = get_adj(out, (int)m);
    for (int i = 0; i <= m; ++i) {
        for (int j = i + 1; j <= m; ++j) {
            if (adj0[i][j] && !adj1[i][j]) {
                quitf(_wa, "Colors %d and %d must be adjacent.", i, j);
            } else if (!adj0[i][j] && adj1[i][j]) {
                quitf(_wa, "Colors %d and %d must not be adjacent.", i, j);
            }
        }
    }

    // Connectivity check
    vector<char> done(m + 1, 0);
    vector<vector<char>> visited(n, vector<char>(n, 0));
    const int di[4] = {0, 1, 0, -1};
    const int dj[4] = {1, 0, -1, 0};

    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < n; ++j) {
            if (!visited[i][j]) {
                long long col = out[i][j];
                if (col > 0) {
                    if (done[(int)col]) {
                        quitf(_wa, "Squares of color %lld are not connected.", col);
                    }
                    done[(int)col] = 1;
                }
                bool outer = false;
                vector<pair<int,int>> st;
                st.emplace_back(i, j);
                visited[i][j] = 1;
                while (!st.empty()) {
                    auto [x, y] = st.back();
                    st.pop_back();
                    for (int d = 0; d < 4; ++d) {
                        int x2 = x + di[d];
                        int y2 = y + dj[d];
                        if (x2 < 0 || x2 >= n || y2 < 0 || y2 >= n) {
                            outer = true;
                        } else if (!visited[x2][y2] && out[x2][y2] == col) {
                            visited[x2][y2] = 1;
                            st.emplace_back(x2, y2);
                        }
                    }
                }
                if (col == 0 && !outer) {
                    quitf(_wa, "Squares of color %lld are not connected.", col);
                }
            }
        }
    }

    // Score: 1 + number of zeros
    long long score = 1;
    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < n; ++j) {
            if (out[i][j] == 0) ++score;
        }
    }

    long long baseline_value = ans.readLong();
    long long best_value = ans.readLong();

    // External calibration anchors do not limit the feasible raw objective.
    double gap = (double)best_value - (double)baseline_value;
    ensuref(gap > 0.0, "Invalid calibration anchors");
    double calibration_ratio = max(0.0, ((double)score - (double)baseline_value) / gap);
    double score_ratio = calibration_ratio <= 1.0 ? 0.6 * calibration_ratio : 0.6 + 0.01 * log(calibration_ratio);
    score_ratio = natural_log_score(100.0 * score_ratio, score - 1, (long double)best_value - 1.0L, false) / 100.0;
    quitp(score_ratio, "Value: %lld. Ratio: %.12f, RatioUnbounded: %.12f", score, score_ratio, score_ratio);
}
