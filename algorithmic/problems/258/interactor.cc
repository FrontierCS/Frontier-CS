#include <cmath>
#include <algorithm>

// Keep historical scores through 60; above the anchor, compare physical objectives.
static double natural_log_score(long double old_points, long double value,
                                long double anchor, bool minimize) {
    if (minimize && value == 0.0L) return 100.0;
    if (old_points <= 60.0L) return (double)std::max(0.0L, old_points);
    if (!(value > 0.0L) || !(anchor > 0.0L))
        return (double)std::clamp(old_points, 0.0L, 100.0L);
    const long double improvement = minimize
        ? std::log(anchor) - std::log(value)
        : std::log(value) - std::log(anchor);
    return (double)std::clamp(60.0L + improvement, 0.0L, 100.0L);
}

#include <cmath>
#include <algorithm>
#include "testlib.h"
#include <vector>
#include <iostream>
#include <queue>
#include <algorithm>
#include <cmath>
#include <iomanip>

// Historical calibration supplies the unchanged low-score branch.
static double calibrated(double r) {
    r = std::max(0.0, r);
    return r <= 1.0 ? 0.6 * r : 0.6 + 0.02 * std::log(r);
}

using namespace std;

// BFS to calculate distances from a source node to all other nodes
void bfs(int start, int n, const vector<vector<int>>& adj, vector<int>& dist) {
    fill(dist.begin(), dist.end(), -1);
    queue<int> q;
    q.push(start);
    dist[start] = 0;

    while (!q.empty()) {
        int u = q.front();
        q.pop();

        for (int v : adj[u]) {
            if (dist[v] == -1) {
                dist[v] = dist[u] + 1;
                q.push(v);
            }
        }
    }
}

int main(int argc, char* argv[]) {
    // Initialize testlib environment
    setName("Interactor for 1370F2 with Dynamic Scoring (Base=log2n+1, Zero=n)");
    registerInteraction(argc, argv);

    // Read the number of test cases from the input file
    int t = inf.readInt(1, 10, "t");

    // Send t to the user's standard input
    cout << t << endl;

    double total_score = 0.0;
    long long tot_moves = 0;
    double tot_unbounded_score = 0.0;

    for (int case_idx = 0; case_idx < t; ++case_idx) {
        // --- Read Test Case Data ---
        int n = inf.readInt(2, 1000, "n");

        // Read Hidden Nodes (Interactor only)
        int hidden_u = inf.readInt(1, n, "hidden_u");
        int hidden_v = inf.readInt(1, n, "hidden_v");
        ensuref(hidden_u != hidden_v, "Hidden nodes must be distinct");

        // Read Edges
        vector<vector<int>> adj(n + 1);
        vector<pair<int, int>> edges;
        for (int i = 0; i < n - 1; ++i) {
            int u = inf.readInt(1, n, "u");
            int v = inf.readInt(1, n, "v");
            adj[u].push_back(v);
            adj[v].push_back(u);
            edges.push_back({u, v});
        }

        // --- Send Graph to User ---
        cout << n << endl;
        for (const auto& edge : edges) {
            cout << edge.first << " " << edge.second << endl;
        }

        // --- Precompute Distances ---
        vector<int> dist_u(n + 1), dist_v(n + 1);
        bfs(hidden_u, n, adj, dist_u);
        bfs(hidden_v, n, adj, dist_v);

        // --- Scoring Parameters for this N ---
        // Base Limit: ceil(log2(n)) + 1
        // Zero Limit: n
        int limit_base = (int)ceil(log2((double)n)) / 2;
        limit_base /= 2;
        int limit_zero = limit_base * 16;

        // Hard limit to prevent infinite loops (set slightly above Zero Limit)
        int hard_limit = n + 50;

        // --- Interaction Loop ---
        int queries = 0;
        bool solved = false;

        while (true) {
            string type = ouf.readToken("[?!]");

            if (type == "?") {
                queries++;

                int c = ouf.readInt(1, n, "c");
                vector<int> query_nodes(c);
                vector<bool> used(n + 1, false);

                int best_node = -1;
                int min_dist_sum = 1e9;

                for (int i = 0; i < c; ++i) {
                    int node = ouf.readInt(1, n, "query_node");
                    if (used[node]) {
                        quitf(_wa, "Test Case %d: Duplicate node %d in query", case_idx + 1, node);
                    }
                    used[node] = true;
                    query_nodes[i] = node;

                    int current_dist_sum = dist_u[node] + dist_v[node];
                    if (current_dist_sum < min_dist_sum) {
                        min_dist_sum = current_dist_sum;
                        best_node = node;
                    }
                }

                // Enforce hard limit
                if (queries > hard_limit) {
                    cout << "-1 -1" << endl;
                    quitf(_wa, "Test Case %d: Query limit exceeded (>%d)", case_idx + 1, hard_limit);
                }

                cout << best_node << " " << min_dist_sum << endl;
            }
            else if (type == "!") {
                int guess_1 = ouf.readInt(1, n, "guess_1");
                int guess_2 = ouf.readInt(1, n, "guess_2");

                bool correct = (guess_1 == hidden_u && guess_2 == hidden_v) ||
                               (guess_1 == hidden_v && guess_2 == hidden_u);

                if (correct) {
                    cout << "Correct" << endl;
                    solved = true;
                } else {
                    cout << "Incorrect" << endl;
                    quitf(_wa, "Test Case %d: Wrong guess. Expected {%d, %d}, got {%d, %d}",
                          case_idx + 1, hidden_u, hidden_v, guess_1, guess_2);
                }
                break;
            }
        }

        tot_moves += queries;

        // A zero-query anchor is a true cost lower bound for small n.
        double case_score;
        if (limit_base == 0) {
            case_score = solved && queries == 0 ? 1.0 : 0.0;
        } else {
            double r = std::max(0.0, (double(limit_zero) - queries) / (limit_zero - limit_base));
            case_score = solved ? calibrated(r * r) : 0.0;
            if (solved) case_score = natural_log_score(100.0L * (case_score), queries, limit_base, true) / 100.0;
        }
        total_score += case_score;
        tot_unbounded_score += case_score;
    }

    // --- Final Verdict ---
    double score_ratio = total_score / (double)t;
    double unbounded_score_ratio = tot_unbounded_score / (double)t;

    // Output final score
    quitp(score_ratio, "Queries: %lld. Ratio: %.12f, RatioUnbounded: %.12f", tot_moves, score_ratio, unbounded_score_ratio);

    return 0;
}
