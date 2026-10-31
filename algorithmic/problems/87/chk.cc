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

#include<bits/stdc++.h>
#include "testlib.h"
using namespace std;

// Calibrate a feasible performance reference to 60 percent.
static double referenceScore(double ratio) {
    return ratio <= 1.0 ? 0.6 * ratio : (0.6 + 0.02 * std::log(ratio));
}

int n, m, ref_k;
vector<int> initial_state, target_state;
vector<vector<int>> adj;

bool isValidTransformation(const vector<int>& stateA, const vector<int>& stateB) {
    // Check if stateB can be obtained from stateA by a valid transformation
    for (int i = 0; i < n; i++) {
        if (stateB[i] == stateA[i]) {
            continue; // Node i kept its color
        }
        // Node i changed its color, check if it's from a neighbor
        bool foundNeighbor = false;
        for (int j : adj[i]) {
            if (stateA[j] == stateB[i]) {
                foundNeighbor = true;
                break;
            }
        }
        if (!foundNeighbor) {
            return false;
        }
    }
    return true;
}

int main(int argc, char* argv[]) {
    registerTestlibCmd(argc, argv);

    // Read input
    n = inf.readInt();
    m = inf.readInt();

    initial_state.resize(n);
    for (int i = 0; i < n; i++) {
        initial_state[i] = inf.readInt();
        if (initial_state[i] != 0 && initial_state[i] != 1) {
            quitf(_fail, "Invalid initial color at node %d: %d", i+1, initial_state[i]);
        }
    }

    target_state.resize(n);
    for (int i = 0; i < n; i++) {
        target_state[i] = inf.readInt();
        if (target_state[i] != 0 && target_state[i] != 1) {
            quitf(_fail, "Invalid target color at node %d: %d", i+1, target_state[i]);
        }
    }

    adj.resize(n);
    for (int i = 0; i < m; i++) {
        int u = inf.readInt() - 1; // Convert to 0-indexed
        int v = inf.readInt() - 1;
        if (u < 0 || u >= n || v < 0 || v >= n || u == v) {
            quitf(_fail, "Invalid edge in input: (%d, %d)", u+1, v+1);
        }
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    // Read reference answer
    ref_k = ans.readInt();
    if (ref_k < 0) quitf(_fail, "Reference steps must be nonnegative");

    // Read participant's output
    if (ouf.seekEof()) {
        quitf(_wa, "No output provided");
    }

    int participant_k = ouf.readInt();

    if (participant_k < 0) {
        quitf(_wa, "Number of steps cannot be negative: %d", participant_k);
    }

    if (participant_k > 20000) {
        quitf(_wa, "Number of steps exceeds limit: %d > 20000", participant_k);
    }

    vector<vector<int>> states(participant_k + 1, vector<int>(n));

    for (int step = 0; step <= participant_k; step++) {
        if (ouf.seekEof()) {
            quitf(_wa, "Expected %d states (k+1), but only found %d", participant_k + 1, step);
        }

        for (int i = 0; i < n; i++) {
            states[step][i] = ouf.readInt();
            if (states[step][i] != 0 && states[step][i] != 1) {
                quitf(_wa, "Invalid color at step %d, node %d: %d (must be 0 or 1)", step, i+1, states[step][i]);
            }
        }
    }

    if (!ouf.seekEof()) {
        quitf(_wa, "Extra output found after %d states", participant_k + 1);
    }

    // Validate first state matches initial state
    if (states[0] != initial_state) {
        quitf(_wa, "First state does not match the initial state");
    }

    // Validate last state matches target state
    if (states[participant_k] != target_state) {
        quitf(_wa, "Last state does not match the target state");
    }

    // Validate each transformation
    for (int step = 0; step < participant_k; step++) {
        if (!isValidTransformation(states[step], states[step + 1])) {
            quitf(_wa, "Invalid transformation from step %d to step %d", step, step + 1);
        }
    }

    // Calculate score
    double score_ratio = referenceScore(((double)ref_k + 1.0) / ((double)participant_k + 1.0));
    score_ratio = natural_log_score(100.0 * score_ratio, participant_k, ref_k, true) / 100.0;
    double unbounded_ratio = score_ratio;

    quitp(score_ratio, "Steps: %d. Ratio: %.12f, RatioUnbounded: %.12f", participant_k, score_ratio, unbounded_ratio);

    return 0;
}
