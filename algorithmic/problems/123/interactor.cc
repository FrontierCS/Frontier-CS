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
#include <chrono>
#include <vector>
#include <string>

#ifdef _WIN32
#include <process.h> // _getpid()
#else
#include <unistd.h>  // getpid()

// Reference calibration: 60 points at r=1, logarithmic rewards above it.
static double calibrated(double r) {
    r = std::max(0.0, r);
    return r <= 1.0 ? 0.6 * r : 0.6 + 0.02 * std::log(r);
}
#endif

using namespace std;

struct LiarScheduler {
    bool lastWasLie = false;
    int pTruthPermille;                 // 0..1000
    explicit LiarScheduler(int p = 500) : pTruthPermille(p) {}
    bool nextTruth() {
        if (lastWasLie) { lastWasLie = false; return true; }
        int r = rnd.next(0, 999);
        bool truth = (r < pTruthPermille);
        lastWasLie = !truth;
        return truth;
    }
};

int main(int argc, char* argv[]) {
    setName("Liar game interactor");
    registerInteraction(argc, argv);

    // Public input (from tests)
    int n = inf.readInt(1, 100000, "n");

    // .ans format: EXACTLY TWO TOKENS:
    //   1) best_queries (nonnegative, used for scoring)
    //   2) hidden_x  (in [1..n])
    long long best_queries = ans.readLong();
    int hidden_x = ans.readInt(1, n, "hidden_x");

    // Seed rnd deterministically enough (no optional controls)
    unsigned long long seed =
            (unsigned long long)chrono::steady_clock::now().time_since_epoch().count();
#ifdef _WIN32
    seed ^= (unsigned long long)_getpid();
#else
    seed ^= (unsigned long long)getpid();
#endif
    rnd.setSeed((long long)seed);

    // Send n to the participant and FLUSH.
    cout << n << endl;

    LiarScheduler liar(500); // 50% truth

    const int MAX_QUESTIONS = 53; // counts only '?'
    const int MAX_GUESSES   = 2;

    long long question_count = 0;
    int guess_count = 0;

    while (true) {
        // Read the next action: must be "?" or "!"
        string action = ouf.readToken(); // token (skips spaces/newlines)
        if (action != "?" && action != "!") {
            quitf(_wa, "Invalid action '%s': expected '?' or '!'.", action.c_str());
        }

        if (action == "?") {
            int k = ouf.readInt(1, n, "k");
            vector<int> S(k);
            vector<char> inSet(n + 1, 0);
            for (int i = 0; i < k; ++i) {
                S[i] = ouf.readInt(1, n, "S[i]");
                if (inSet[S[i]]) quitf(_wa, "Invalid query: duplicate element %d.", S[i]);
                inSet[S[i]] = 1;
            }

            ++question_count;
            if (question_count > MAX_QUESTIONS) {
                quitp(0.0,
                      "Query limit exceeded: used %lld (> %d). Ratio: 0.0000",
                      question_count, MAX_QUESTIONS);
            }

            bool actual = (inSet[hidden_x] != 0);
            bool truthful = liar.nextTruth();
            bool replyYes = truthful ? actual : !actual;

            // Answer and FLUSH
            cout << (replyYes ? "YES" : "NO") << endl;

        } else { // action == "!"
            int g = ouf.readInt(1, n, "guess");
            ++guess_count;
            if (guess_count > MAX_GUESSES) {
                quitp(0.0, "Guess limit exceeded. Max guesses: %d. Ratio: 0.0000", MAX_GUESSES);
            }

            if (g == hidden_x) {
                cout << ":)" << endl;

                long long your_queries = question_count; // guesses DO NOT count
                if (your_queries > MAX_QUESTIONS) {
                    quitp(0.0,
                          "Correct guess, but exceeded %d questions. Questions used: %lld. Ratio: 0.0000",
                          MAX_QUESTIONS, your_queries);
                }

                double your_value = double(MAX_QUESTIONS - your_queries);
                double best_value = double(MAX_QUESTIONS - best_queries);

                if (best_value <= 0) quitf(_fail, "Reference questions must be below 53");
                double score_ratio = calibrated(your_value / best_value);
    score_ratio = natural_log_score(100.0 * score_ratio, your_queries, best_queries, true) / 100.0;
                double unbounded_ratio = score_ratio;

                quitp(score_ratio, "Correct guess in %lld questions. Ratio: %.12f, RatioUnbounded: %.12f",
                      your_queries, score_ratio, unbounded_ratio);
            } else {
                cout << ":(" << endl;
                if (guess_count == MAX_GUESSES) {
                    quitp(0.0, "Wrong guess. Ratio: 0.0000");
                }
            }
        }
    }
}
