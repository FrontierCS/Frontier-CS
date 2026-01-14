#include <iostream>
#include <vector>
#include <numeric>
#include <cmath>
#include <algorithm>

using namespace std;

int N;
vector<int> S_init;
int M;
vector<pair<int, int>> JerryMoves;

struct Swap {
    int u, v;
};

// Global variables for simulation to prevent frequent reallocations
vector<int> P;
vector<int> pos;
vector<int> val_cost; 
vector<vector<int>> buckets;
int min_bucket;
int active_bad_count;

// Add a value to the bucket corresponding to its cost
void add_to_bucket(int v, int c) {
    if (c <= N) { // Should always be true as cost < N
        buckets[c].push_back(v);
        if (c < min_bucket) min_bucket = c;
    }
}

// Re-evaluate the cost of fixing value v and update structures
void update_val(int v) {
    int c = abs(pos[v] - v);
    int old = val_cost[v];
    
    if (pos[v] == v) {
        if (old != -1) {
            active_bad_count--;
            val_cost[v] = -1;
        }
    } else {
        if (old == -1) {
            active_bad_count++;
        }
        val_cost[v] = c;
        add_to_bucket(v, c);
    }
}

// Simulate the process for R rounds using a greedy strategy
// Returns total distance cost if successful, -1 otherwise.
long long solve(int R, vector<Swap>& user_moves) {
    // 1. Compute sigma: the mapping of indices from time 0 to time R due to Jerry's moves
    vector<int> perm(N);
    iota(perm.begin(), perm.end(), 0);
    for (int k = 0; k < R; ++k) {
        int a = JerryMoves[k].first;
        int b = JerryMoves[k].second;
        swap(perm[a], perm[b]);
    }

    // 2. Compute initial P
    // P[i] is the target value that should be at index i relative to the sorted state at round R.
    // Specifically P corresponds to "value at index i needs to be value P[i] eventually".
    // Or more precisely: P[i] is the value v such that pos[v] = i.
    // We compute P such that P[i] is the value currently at i, mapped back from target.
    // Actually, following the logic: P[i] is the "virtual value" at index i.
    // We want P to become Identity.
    vector<int> inv_perm(N);
    for (int i = 0; i < N; ++i) {
        inv_perm[perm[i]] = i;
    }
    
    for (int i = 0; i < N; ++i) {
        P[i] = inv_perm[S_init[i]];
        pos[P[i]] = i;
    }

    // 3. Initialize buckets for greedy selection
    for (int i = 0; i <= N; ++i) buckets[i].clear();
    min_bucket = N + 1;
    active_bad_count = 0;
    
    // Using -2 as a temporary sentinel
    fill(val_cost.begin(), val_cost.end(), -2); 

    for (int v = 0; v < N; ++v) {
        val_cost[v] = -1; 
        int c = abs(pos[v] - v);
        if (c > 0) {
            val_cost[v] = c;
            add_to_bucket(v, c);
            active_bad_count++;
        }
    }

    user_moves.clear();
    if (user_moves.capacity() < R) user_moves.reserve(R);
    long long total_dist = 0;

    for (int k = 0; k < R; ++k) {
        int u = 0, v = 0;
        
        // Strategy: Fix the element with the smallest displacement cost
        int best_val = -1;
        
        // Find min cost fix
        while (min_bucket <= N) {
            if (buckets[min_bucket].empty()) {
                min_bucket++;
                continue;
            }
            int cand = buckets[min_bucket].back();
            buckets[min_bucket].pop_back();
            
            // Lazy deletion check
            if (val_cost[cand] == min_bucket) {
                best_val = cand;
                break;
            }
        }
        
        if (best_val != -1) {
            v = best_val;     // The value we want to fix
            u = pos[v];       // Current position of value v
            
            // We swap indices u and v.
            // This moves value v to index v (fixing it).
            // Value at v (let's call it other) moves to u.
            
            int V_u = P[u]; // should be v
            int V_v = P[v]; 
            
            swap(P[u], P[v]);
            pos[V_u] = v;
            pos[V_v] = u;
            
            update_val(V_u);
            update_val(V_v);
            
            total_dist += abs(u - v);
        } else {
            // Already sorted or no bad elements, perform dummy swap (0, 0)
        }
        
        user_moves.push_back({u, v});

        // Apply Jerry's move for this round
        if (k < M) {
            int A = JerryMoves[k].first;
            int B = JerryMoves[k].second;
            
            // 1. Index swap (A, B) - swaps values at these locations
            int valA = P[A];
            int valB = P[B];
            swap(P[A], P[B]);
            pos[valA] = B;
            pos[valB] = A;
            update_val(valA);
            update_val(valB);

            // 2. Value relabeling A <-> B - swaps the identity of values A and B
            int pA = pos[A];
            int pB = pos[B];
            P[pA] = B;
            P[pB] = A;
            pos[B] = pA;
            pos[A] = pB;
            update_val(A);
            update_val(B);
        }
    }

    if (active_bad_count == 0) return total_dist;
    return -1;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> N)) return 0;
    S_init.resize(N);
    for (int i = 0; i < N; ++i) cin >> S_init[i];
    cin >> M;
    JerryMoves.resize(M);
    for (int i = 0; i < M; ++i) cin >> JerryMoves[i].first >> JerryMoves[i].second;

    P.resize(N);
    pos.resize(N);
    val_cost.resize(N);
    buckets.resize(N + 1);

    // Binary search for the minimal R
    int low = 0, high = M;
    int best_R = M;
    vector<Swap> dummy_moves;
    
    while (low <= high) {
        int mid = low + (high - low) / 2;
        if (solve(mid, dummy_moves) != -1) {
            best_R = mid;
            high = mid - 1;
        } else {
            low = mid + 1;
        }
    }

    // Retrieve solution for best_R
    vector<Swap> final_moves;
    long long dist = solve(best_R, final_moves);
    
    cout << best_R << "\n";
    for (auto& m : final_moves) {
        cout << m.u << " " << m.v << "\n";
    }
    long long V = (long long)best_R * dist;
    cout << V << "\n";

    return 0;
}