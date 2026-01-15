#include <iostream>
#include <vector>
#include <algorithm>
#include <random>
#include <map>

using namespace std;

int n;
// We track queries implicitly via interaction, but for logic we just output.

int ask(int u, int v) {
    if (u == v) return 0;
    cout << "? " << u << " " << v << endl;
    int dist;
    cin >> dist;
    return dist;
}

void report(int x) {
    cout << "! " << x << endl;
    exit(0);
}

// Check if u is ancestor of v given their depths
bool is_ancestor(int u, int v, int d_u, int d_v) {
    int d = ask(u, v);
    return d == d_v - d_u;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> n)) return 0;

    if (n == 1) report(1);

    // Get depths from node 1
    vector<int> depth(n + 1);
    depth[1] = 0;
    vector<vector<int>> layers(n + 1);
    layers[0].push_back(1);

    int max_depth = 0;
    for (int i = 2; i <= n; ++i) {
        int d = ask(1, i);
        depth[i] = d;
        layers[d].push_back(i);
        max_depth = max(max_depth, d);
    }

    int curr = 1;
    mt19937 rng(1337);

    // We traverse down finding the heavy child
    while (true) {
        int next_depth = depth[curr] + 1;
        
        // If no children, current is centroid
        if (next_depth > max_depth || layers[next_depth].empty()) {
            report(curr);
        }

        vector<int>& candidates = layers[next_depth];
        
        // If only one child, move there (size must be > N/2 if parent was)
        // Actually, this optimization is only safe if we assume we are on heavy path.
        // But if we came from heavy parent, and there is only 1 child, it must be heavy?
        // Not necessarily, could be size <= N/2. But if only 1 child, and N is large...
        // Safest is to treat it as candidate.
        // However, checking size is expensive. 
        // Let's rely on the loop: if it's the only one, we just verify it.
        
        vector<int> active_candidates = candidates;
        bool found_next = false;
        
        // Strategy: Pick random node x. Find its ancestor among candidates.
        // If ancestor found, verify if it's heavy.
        
        int attempts = 0;
        // Total prob of landing in heavy subtree > 0.5. 
        // 20-30 attempts should be enough to find it if it exists.
        while (!active_candidates.empty() && attempts < 30) {
            attempts++;
            int x = std::uniform_int_distribution<int>(1, n)(rng);
            
            // Optimization: if x is not deeper than candidates, it can't be descendant
            if (depth[x] <= next_depth) continue;

            // Shuffle candidates to check random one first
            shuffle(active_candidates.begin(), active_candidates.end(), rng);
            
            int candidate_hit = -1;
            
            for (int cand : active_candidates) {
                if (is_ancestor(cand, x, next_depth, depth[x])) {
                    candidate_hit = cand;
                    break;
                }
            }
            
            if (candidate_hit != -1) {
                // Verify candidate
                int check_samples = 20; // Reduced for speed
                int hits = 0;
                for (int k = 0; k < check_samples; ++k) {
                    int rx = std::uniform_int_distribution<int>(1, n)(rng);
                    if (depth[rx] <= next_depth) continue;
                    if (is_ancestor(candidate_hit, rx, next_depth, depth[rx])) {
                        hits++;
                    }
                }
                
                // If hits/samples approx > 0.5. Use 0.4 threshold.
                if (hits >= check_samples * 0.4) {
                    curr = candidate_hit;
                    found_next = true;
                    break;
                } else {
                    // It was a light child
                    // Remove from active
                    auto it = std::find(active_candidates.begin(), active_candidates.end(), candidate_hit);
                    if (it != active_candidates.end()) active_candidates.erase(it);
                }
            }
        }

        if (!found_next) {
            // No heavy child found
            report(curr);
        }
    }

    return 0;
}