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

#include <csignal>
#include <cstddef>
#include <cstdio>
#include <cstdlib>
#include <iostream>
#include <vector>
#include <string>
#include "testlib.h"

// Reference calibration: 60 points at r=1, logarithmic rewards above it.
static double calibrated(double r) {
    r = std::max(0.0, r);
    return r <= 1.0 ? 0.6 * r : 0.6 + 0.02 * std::log(r);
}
using namespace std;

enum {
    INVALID_INPUT = -1,
    INVALID_T_LENGTH = 1,
    INVALID_T_CHAR   = 2,
    WRONG_T          = 3,
    INVALID_S_LENGTH = 4,
    INVALID_S_CHAR   = 5,
    QUERY_LIMIT_EXCEEDED = 6,
    INVALID_OUTPUT   = 9,
};

const int N_MAX = 8000;
const int QUERY_LIMIT = 5000;

int N, R;
std::vector<int> U, V;
std::string T;
int QUERY_COUNT = 0;

double score(int x){ return natural_log_score(100.0 * calibrated((5000.0-x)/4100.0), x, 900.0L, true) / 100.0; }
double score_unbounded(int x){ return score(x); }

[[noreturn]] void wrong(const int num) {
    fprintf(stdout, "-1\n");
    fflush(stdout);
    quitf(_wa, "translate:wrong\nWrong Answer [%d]\n", num);
}

[[noreturn]] void ok() {
    double r  = score(QUERY_COUNT);
    double ru = score_unbounded(QUERY_COUNT);
    quitp(r, "Ratio: %.12f , RatioUnbounded: %.12f , Queries: %d", r, ru, QUERY_COUNT);
}

int query(std::string s) {
    const int M = 2 * N + 1;
    if ((int)s.size() != M) {
        wrong(INVALID_S_LENGTH);
    }
    for (char c : s) {
        if (c != '0' && c != '1') wrong(INVALID_S_CHAR);
    }
    if (QUERY_COUNT == QUERY_LIMIT) {
        wrong(QUERY_LIMIT_EXCEEDED);
    }
    QUERY_COUNT++;

    for (char &c : s) c -= '0';

    for (int i = N - 1; i >= 0; --i) {
        const int u = U[i], v = V[i];
        if (T[i] == '&') {
            s[i] ^= (s[u] & s[v]);
        } else {
            s[i] ^= (s[u] | s[v]);
        }
    }
    return s[0];
}

void answer(std::string t) {
    if ((int)t.size() != N) {
        wrong(INVALID_T_LENGTH);
    }
    for (char c : t) {
        if (c != '&' && c != '|') wrong(INVALID_T_CHAR);
    }
    if (t != T) {
        wrong(WRONG_T);
    }
    ok();
}

int main(int argc, char* argv[]) {
    registerInteraction(argc, argv);
    // A contestant may exit immediately after its final answer. A notification
    // to the closed pipe must not kill the interactor before its verdict.
    std::signal(SIGPIPE, SIG_IGN);

    N = inf.readInt();
    R = inf.readInt();
    if (N < 1 || N > N_MAX) {
        wrong(INVALID_INPUT);
    }
    cout << N << " " << R << endl;

    U.resize(N);
    V.resize(N);
    for (int i = 0; i < N; ++i) {
        U[i] = inf.readInt();
        V[i] = inf.readInt();
        cout << U[i] << " " << V[i] << endl;
    }

    T = inf.readToken();
    if ((int)T.size() != N) {
        wrong(INVALID_INPUT);
    }
    int orCount = 0;
    for (char c : T) {
        if (c != '&' && c != '|') wrong(INVALID_INPUT);
        if (c == '|') ++orCount;
    }
    if (orCount > R) {
        wrong(INVALID_INPUT);
    }

    while (true) {
        std::string op = ouf.readToken();
        if (op.empty()) wrong(INVALID_OUTPUT);
        const char type = op[0];
        if (type != '?' && type != '!') wrong(INVALID_OUTPUT);

        std::string payload = ouf.readToken();

        if (!payload.empty() && payload.back() == '\n') payload.pop_back();

        if (type == '?') {
            int res = query(payload);
            fprintf(stdout, "%d\n", res);
            fflush(stdout);
        } else {
            answer(payload);
        }
    }
}
