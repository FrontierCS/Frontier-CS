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
#include <vector>

const int MAXLOG = 10;

std::vector<std::vector<int>> adj;
int n;
std::vector<int> depth;
std::vector<std::vector<int>> up; // up[node][i] = 2^i-th ancestor of node

void dfs(int u, int parent) {
    up[u][0] = parent;
    for (int i = 1; i < MAXLOG; ++i) {
        if (up[u][i-1] != -1) {
            up[u][i] = up[up[u][i-1]][i-1];
        }
    }

    for (int v : adj[u]) {
        if (v != parent) {
            depth[v] = depth[u] + 1;
            dfs(v, u);
        }
    }
}

int lca(int u, int v) {
    if (depth[u] < depth[v]) std::swap(u, v);

    // Bring u to the same level as v
    int diff = depth[u] - depth[v];
    for (int i = 0; i < MAXLOG; ++i) {
        if ((diff >> i) & 1) {
            u = up[u][i];
        }
    }

    if (u == v) return u;

    // Binary search for LCA
    for (int i = MAXLOG - 1; i >= 0; --i) {
        if (up[u][i] != up[v][i]) {
            u = up[u][i];
            v = up[v][i];
        }
    }

    return up[u][0];
}


// Map normalized performance to the reference-anchored score, without a cap.
static double referenceScore(double r) {
    return r <= 1.0 ? 0.6 * r : (0.6 + 0.02 * std::log(r));
}

int main(int argc, char* argv[]) {
    registerInteraction(argc, argv);

    n = inf.readInt();

    adj.resize(n + 1);
    for (int i = 0; i < n - 1; ++i) {
        int u = inf.readInt();
        int v = inf.readInt();
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    // Preprocess LCA
    depth.resize(n + 1);
    up.assign(n + 1, std::vector<int>(MAXLOG, -1));
    depth[1] = 0;
    dfs(1, -1);

    long long ref_queries = ans.readLong();
    ensuref(ref_queries >= 0, "Reference query count must be nonnegative");

    println(n);

    const int MAX_QUERIES = 20000;
    int query_count = 0;

    while (true) {
        int action_type = ouf.readInt();

        if (action_type == 0) { // Query
            if (++query_count > MAX_QUERIES) {
                quitp(0.0, "Query limit exceeded. Max queries: %d. Ratio: 0.0000", MAX_QUERIES);
            }

            int a = ouf.readInt();
            int b = ouf.readInt();
            int c = ouf.readInt();

            // Validate query
            if (a < 1 || a > n || b < 1 || b > n || c < 1 || c > n) {
                quitf(_wa, "Invalid query: nodes must be in range [1, %d]", n);
            }
            if (a == b || b == c || a == c) {
                quitf(_wa, "Invalid query: the three nodes must be distinct");
            }

            // Find the three pairwise LCAs
            int lca_ab = lca(a, b);
            int lca_bc = lca(b, c);
            int lca_ac = lca(a, c);

            // The answer is the LCA with the maximum depth (deepest one)
            int answer = lca_ab;
            if (lca_ab == lca_ac) {
                answer = lca_bc;
            }
            else if (lca_ab == lca_bc) {
                answer = lca_ac;
            }

            println(answer);

        } else if (action_type == 1) { // Final answer
            std::vector<std::pair<int, int>> submitted_edges;

            for (int i = 0; i < n - 1; ++i) {
                int u = ouf.readInt();
                int v = ouf.readInt();

                if (u < 1 || u > n || v < 1 || v > n) {
                    quitf(_wa, "Invalid edge: nodes must be in range [1, %d]", n);
                }
                if (u == v) {
                    quitf(_wa, "Invalid edge: self-loop detected");
                }

                // Normalize edges (smaller node first)
                submitted_edges.push_back({std::min(u, v), std::max(u, v)});
            }

            // Sort submitted edges for comparison
            std::sort(submitted_edges.begin(), submitted_edges.end());

            // Check for duplicate edges
            for (int i = 1; i < (int)submitted_edges.size(); ++i) {
                if (submitted_edges[i] == submitted_edges[i-1]) {
                    quitf(_wa, "Invalid answer: duplicate edge (%d, %d)",
                          submitted_edges[i].first, submitted_edges[i].second);
                }
            }

            // Build correct edge list from the hidden tree
            std::vector<std::pair<int, int>> correct_edges;
            for (int u = 1; u <= n; ++u) {
                for (int v : adj[u]) {
                    if (u < v) {
                        correct_edges.push_back({u, v});
                    }
                }
            }
            std::sort(correct_edges.begin(), correct_edges.end());

            // Compare the two edge lists
            if (submitted_edges == correct_edges) {
                long long your_queries = query_count;

                double normalized_performance = ((double)ref_queries + 1.0) / ((double)your_queries + 1.0);
                double score_ratio = referenceScore(normalized_performance);
    score_ratio = natural_log_score(100.0 * score_ratio, your_queries, ref_queries, true) / 100.0;
                double unbounded_ratio = score_ratio;

                quitp(score_ratio, "Correct tree in %lld queries. Ratio: %.12f, RatioUnbounded: %.12f", your_queries, score_ratio, unbounded_ratio);
            } else {
                quitp(0.0, "Wrong tree structure. Ratio: 0.0000");
            }
            break;

        } else {
            quitf(_wa, "Invalid action type: expected 0 or 1, but got %d", action_type);
        }
    }

    return 0;
}
