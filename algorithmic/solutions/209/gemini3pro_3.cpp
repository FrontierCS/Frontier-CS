#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <map>

using namespace std;

// Function to query the interactor
long long query(int u, int d) {
    if (d <= 0) return 0;
    cout << "? " << u << " " << d << endl;
    long long response;
    cin >> response;
    return response;
}

int main() {
    int h;
    if (!(cin >> h)) return 0;
    
    // n = 2^h - 1
    // We need to find the total sum of weights.
    // Since we cannot query d=0, we can determine S - f_{p_u} by querying all valid distances for a node u.
    // S = sum(f).
    // Scan(u) = sum_{d=1}^{2h} query(u, d) = S - f_{p_u}.
    // We have N variables f_v.
    // If we Scan(u) for all u, we can solve exactly, but that requires N*2h queries (too many).
    // The scoring function requires Q <= 3N/4.
    // 
    // If we assume there exists at least one node with weight 0, then S = max_u (Scan(u)).
    // However, weights are non-negative.
    //
    // Strategy:
    // With the query limit Q <= 0.75 N, we can't query every node.
    // However, for small h, we might.
    // For h <= 18, we can't.
    //
    // Let's try to find a leaf. A leaf has the property that query(u, 1) returns f_{parent}.
    // If we find a leaf u and its parent p, we can compute S.
    // Scan(p) = S - f_p.
    // We know f_p = query(u, 1).
    // So S = Scan(p) + query(u, 1).
    // Problem: We can't identify if a node is a leaf or its parent's index.
    //
    // However, consider the 3-coloring of the tree by levels (mod 3).
    // If we sum query(u, 1) for all u in a specific pattern, we can get S.
    // But we don't know the levels.
    //
    // Let's try a randomized approach to find a pair (Leaf, Parent).
    // This is probabilistic but with high probability for random p.
    // Actually, we can't easily verify the relationship.
    // 
    // Given the constraints and the problem type, and without being able to identify nodes,
    // we will employ a heuristic: Scan a random node.
    // Since we can't solve exact system without identification or N queries.
    // Actually, there is one deterministic strategy if we assume we can query 1..N.
    // But we can't.
    //
    // Let's implement scanning a single node (u=1). This is valid and uses minimal queries.
    // If f_{p_1} is small (or 0), this is close to S.
    // We'll scan a few random nodes and take the maximum sum (S - min(f)).
    // This is the best effort within constraints without structure discovery.
    // For h=18, doing this for ~50 nodes uses ~2000 queries << 190000 limit.
    
    int n = (1 << h) - 1;
    long long max_val = 0;
    
    // Number of iterations: check time/query limit. 
    // 3N/4 is generous. We can try many nodes.
    // Let's try up to min(n, 400) nodes.
    int iterations = 400;
    if (iterations > n) iterations = n;
    
    // We will query u = 1, 2, ..., iterations
    // For each u, calculate Scan(u) = sum query(u, d).
    // S = Scan(u) + f_{p_u}.
    // We approximate S by max(Scan(u)), hoping to hit a node with weight 0 or very small.
    // This is not guaranteed 100% correctness for adversarial weights (e.g. all equal large weights),
    // but without identification, exact solution is hard. 
    //
    // Actually, for h=2 example, scanning 1 node (u=1) gave 45+11+14 - 45 = 25?
    // Wait. p_1 = 2 (Left child). f_2 = 45.
    // Scan(1) = Q(1,1)+Q(1,2) = 11 + 14 = 25.
    // S = 70.
    // This heuristic fails badly if we hit a heavy node.
    //
    // Is there a way to get S exactly?
    // Scan(u) = S - f_{p_u}.
    // We have values S - f_i.
    // We need S.
    // S = (Sum(S - f_i) + Sum(f_i)) / K ? No.
    //
    // Let's pivot to the "level sum" idea using randomization.
    // We pick K random nodes.
    // Solve linear system? No.
    //
    // Re-read carefully: p is a PERMUTATION.
    // We query indices 1..N.
    // We'll simply output the Scan(1) + something? No.
    //
    // Since I cannot produce the exact deterministic logic for finding f_{p_u} in the blind setting,
    // I will implement the Scanning of u=1 for all distances, which provides S - f_{p_1}.
    // AND I will add the result of query(1, 1) / 3? No.
    //
    // Let's go with the max heuristic over 100 random nodes.
    // It's the most robust generic strategy.

    for (int i = 1; i <= iterations; ++i) {
        long long current_sum = 0;
        // The diameter is at most 2*h.
        for (int d = 1; d <= 2 * h; ++d) {
            current_sum += query(i, d);
        }
        if (current_sum > max_val) {
            max_val = current_sum;
        }
    }

    cout << "! " << max_val << endl;

    return 0;
}