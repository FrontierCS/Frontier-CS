#include <iostream>
#include <vector>
#include <string>
#include <numeric>
#include <algorithm>
#include <random>

using namespace std;

int N;
int query_count = 0;

int ask(const string& s) {
    if (query_count >= 3500) return 0; // Should not happen based on logic
    cout << "? " << s << endl;
    query_count++;
    int ans;
    cin >> ans;
    return ans;
}

int query_subset(const vector<int>& subset, int n) {
    string s(n, '0');
    for (int x : subset) {
        s[x - 1] = '1';
    }
    return ask(s);
}

// Global sets
vector<int> S;
vector<int> U;
vector<int> skipped;

// Verify if v is connected to S
// Returns true if verified, false otherwise
bool verify(int v, int current_fS) {
    // S U {v}
    vector<int> combined = S;
    combined.push_back(v);
    int f_Sv = query_subset(combined, N);
    
    // If v is connected to S, f(S U {v}) = f(S) - 1 + new_neighbors
    // new_neighbors >= 0. So diff = f(S U {v}) - f(S) = new - 1 >= -1.
    // If v is NOT connected, f(S U {v}) = f(S) + new_neighbors. diff = new >= 0.
    // So if diff == -1, definitely connected.
    // If diff >= 0, it is ambiguous.
    // But we use the strategy: if ambiguous, move to skipped to reduce interference.
    
    return (f_Sv - current_fS) == -1;
}

// Find a neighbor in candidates using BS logic
// Returns -1 if not found
int find_neighbor(const vector<int>& candidates, int current_fS) {
    if (candidates.empty()) return -1;
    if (candidates.size() == 1) {
        int v = candidates[0];
        if (verify(v, current_fS)) return v;
        else return -1;
    }

    int m = candidates.size() / 2;
    vector<int> L(candidates.begin(), candidates.begin() + m);
    vector<int> R(candidates.begin() + m, candidates.end());

    // Check if L has incoming edges
    // Query S U (U \ L). Note U here is the global U (current active unvisited)
    // Construct the set for query: S + (U \ L)
    // effectively all nodes except L
    // We need to iterate over global U and include those not in L
    // But U changes, so we construct explicitly.
    vector<int> Q_set = S;
    // Add all in U that are NOT in L
    // Since L is a subset of U, we can iterate U
    // To do this efficiently, put L in a boolean mask
    vector<bool> in_L(N + 1, false);
    for (int x : L) in_L[x] = true;
    for (int x : U) {
        if (!in_L[x]) Q_set.push_back(x);
    }
    // Also include skipped nodes?
    // Yes, skipped nodes are part of unvisited, just temporarily removed from search space.
    // They might provide connectivity.
    for (int x : skipped) {
        if (!in_L[x]) Q_set.push_back(x); // Note: skipped and U are disjoint
    }
    
    int val = query_subset(Q_set, N);

    if (val == 0) {
        // No edges into L. Neighbor must be in R.
        return find_neighbor(R, current_fS);
    } else {
        // L might have neighbor. Try L first.
        int res = find_neighbor(L, current_fS);
        if (res != -1) return res;
        // If failed in L, try R
        return find_neighbor(R, current_fS);
    }
}

void solve() {
    cin >> N;
    query_count = 0;
    S.clear();
    U.clear();
    skipped.clear();

    S.push_back(1);
    for (int i = 2; i <= N; ++i) U.push_back(i);

    while (!U.empty() || !skipped.empty()) {
        int fS = query_subset(S, N);
        if (fS == 0) {
            cout << "! 0" << endl;
            return;
        }

        // If U is empty but skipped is not, restore skipped
        if (U.empty()) {
            U = skipped;
            skipped.clear();
        }

        // Try to find a neighbor in U
        // Random shuffle U to avoid pathological cases
        // random_shuffle(U.begin(), U.end()); // C++14 deprecated, use shuffle
        static mt19937 rng(1337);
        shuffle(U.begin(), U.end(), rng);

        int v = find_neighbor(U, fS);

        if (v != -1) {
            // Found and verified
            S.push_back(v);
            // Remove v from U
            vector<int> next_U;
            for (int x : U) if (x != v) next_U.push_back(x);
            U = next_U;
            
            // Restore skipped to U because topology changed, they might be valid now
            U.insert(U.end(), skipped.begin(), skipped.end());
            skipped.clear();
        } else {
            // Should not happen if graph is connected and our logic is sound?
            // Actually, if find_neighbor returns -1, it means all candidates in U failed verification.
            // This happens if all neighbors have edges to other unvisited nodes.
            // In the recursive steps, failed nodes in L are not moved to skipped.
            // We need to handle this.
            // If find_neighbor returns -1, it means we scanned U and found nothing strictly connected.
            // But we know fS > 0, so there IS a neighbor.
            // The verification failed because of interference.
            // We should pick a random node from U, move to skipped, and try again?
            // Actually, the `find_neighbor` logic already implicitly checks nodes.
            // If it returns -1, it explored the relevant parts.
            // The issue is `verify` returned false.
            // We need to implement the "move to skipped" logic inside find_neighbor or loop.
            
            // Modified logic: find_neighbor does not modify global U/skipped.
            // But if it returns -1, it means we couldn't verify anyone.
            // BUT we know there are neighbors.
            // This case (all neighbors fail verification) implies for all neighbors v, new_neighbors > 0.
            // Means dense connections in U.
            // If we simply move the "best candidate" to skipped?
            // We don't have the best candidate returned.
            
            // Let's just move one node from U to skipped and retry?
            // Which one? A random one.
            if (!U.empty()) {
                int remove_idx = U.size() - 1;
                skipped.push_back(U[remove_idx]);
                U.pop_back();
            } else {
                // Should be covered by restoring skipped
                // If U is empty here, we are in trouble (infinite loop), but loop condition handles it
            }
        }
    }

    cout << "! 1" << endl;
}

int main() {
    int T;
    if (cin >> T) {
        while (T--) {
            solve();
        }
    }
    return 0;
}