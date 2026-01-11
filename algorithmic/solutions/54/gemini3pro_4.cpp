#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <map>
#include <random>

using namespace std;

int n;
vector<int> depth;
vector<vector<int>> layers;
int query_count = 0;

int ask(int u, int v) {
    if (u == v) return 0;
    cout << "? " << u << " " << v << endl;
    query_count++;
    int d;
    cin >> d;
    return d;
}

// Global cache for distances from current u is not feasible for all, 
// but we only need it for specific checks.
// We'll rely on direct queries or logic.

mt19937 rng(1337);

// Function to find the ancestor of x at depth target_depth (which must be depth[u] + 1)
// Candidates are passed to avoid scanning all layers if possible, but initially we scan layer.
int get_child_towards(int u, int x, const vector<int>& candidates) {
    // We assume x is in subtree of u.
    // The child v satisfies dist(v, x) = dist(u, x) - 1.
    // Also dist(u, x) = depth[x] - depth[u].
    // So dist(v, x) = depth[x] - (depth[u] + 1).
    int target_dist = depth[x] - (depth[u] + 1);
    
    // Optimization: if x is in candidates, it is the child itself.
    if (depth[x] == depth[u] + 1) return x;

    for (int v : candidates) {
        if (ask(v, x) == target_dist) {
            return v;
        }
    }
    return -1;
}

// Returns the centroid if found in subtree of u, otherwise -1.
int solve(int u, vector<int>& samples) {
    // Identify children of u
    if (depth[u] + 1 >= layers.size()) return u; // Leaf
    const vector<int>& children = layers[depth[u] + 1];
    
    if (children.empty()) return u;
    
    // If only one child, no ambiguity
    if (children.size() == 1) {
        // We can pass all valid samples down without checking
        // Filter samples lazily? Or just assume they are valid?
        // Logic requires valid samples to guide deeper.
        // For size 1, we don't need samples to choose.
        // But we need to know if we should stop (is child heavy?).
        // Actually, if only 1 child, it is heavy unless u is centroid.
        // We visit it.
        int res = solve(children[0], samples);
        if (res != -1) return res;
        return u;
    }

    // Multiple children: use samples to pick heavy ones
    map<int, vector<int>> buckets;
    vector<int> current_samples = samples;
    
    // If we have few samples, refill
    // We want at least some samples to guide us.
    // But refilling is expensive if we check validity.
    // We try to use existing samples first.
    
    // For each sample, find its child
    // Optimization: if sample count is high, we might limit checks?
    // But we need to find the heavy child.
    
    int processed = 0;
    for (int x : current_samples) {
        // Verify x is in subtree of u? We assume passed samples are.
        // Find child
        int v = get_child_towards(u, x, children);
        if (v != -1) {
            buckets[v].push_back(x);
        }
        processed++;
        if (processed > 20) break; // Heuristic limit to save queries
    }
    
    // If buckets are empty, we might need refill
    if (buckets.empty()) {
        // Refill strategy
        int refills = 0;
        while (refills < 5 && buckets.empty()) { // Try a few times
            int x = uniform_int_distribution<int>(1, n)(rng);
            // Check if x is in subtree
            if (depth[x] <= depth[u]) continue;
            if (ask(u, x) == depth[x] - depth[u]) {
                int v = get_child_towards(u, x, children);
                if (v != -1) buckets[v].push_back(x);
            }
            refills++;
        }
    }

    // Sort children by vote count
    vector<pair<int, int>> sorted_children;
    for (int v : children) {
        sorted_children.push_back({(int)buckets[v].size(), v});
    }
    sort(sorted_children.rbegin(), sorted_children.rend());
    
    // Visit children
    for (auto p : sorted_children) {
        int v = p.second;
        int count = p.first;
        
        // If count is 0 and we have visited others, maybe skip?
        // But if heavy child had 0 samples (unlikely), we might miss it.
        // However, we must visit at least one.
        // With limited queries, we bet on samples.
        // If we visited a heavy-looking child and it failed, and others have 0, then u is centroid.
        
        // Pass the samples belonging to v
        int res = solve(v, buckets[v]);
        if (res != -1) return res;
        
        // If we failed on the best candidate, and it had significant samples,
        // it's likely u is centroid.
        if (count > 0) return u; 
    }
    
    // If we explored all (or skipped) and found nothing, u is centroid
    return u;
}

int main() {
    cin >> n;
    
    depth.assign(n + 1, 0);
    layers.resize(n + 1);
    layers[0].push_back(1);
    
    for (int i = 2; i <= n; ++i) {
        depth[i] = ask(1, i);
        if (depth[i] < layers.size()) {
            layers[depth[i]].push_back(i);
        } else {
            // Should not happen with resize(n+1)
            layers.resize(depth[i] + 1);
            layers[depth[i]].push_back(i);
        }
    }
    
    // Initial samples
    vector<int> samples;
    int k = min(n, 200); 
    vector<int> p(n);
    iota(p.begin(), p.end(), 1);
    shuffle(p.begin(), p.end(), rng);
    for(int i=0; i<k; ++i) samples.push_back(p[i]);
    
    int ans = solve(1, samples);
    cout << "! " << ans << endl;
    
    return 0;
}